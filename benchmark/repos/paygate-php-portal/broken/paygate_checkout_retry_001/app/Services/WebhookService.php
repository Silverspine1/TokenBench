<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\Payment;
use App\Domain\PaymentStatus;
use App\Payment\GatewayEventNormalizer;
use App\Payment\WebhookVerifier;
use App\Store\Database;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;
use App\Store\PaymentRepository;

final class WebhookService
{
    private Database $db;
    private WebhookVerifier $verifier;
    private GatewayEventNormalizer $normalizer;
    private PaymentRepository $payments;
    private InvoiceRepository $invoices;
    private OrderRepository $orders;
    private IdempotencyService $idempotency;

    public function __construct(
        Database $db,
        WebhookVerifier $verifier,
        GatewayEventNormalizer $normalizer,
        PaymentRepository $payments,
        InvoiceRepository $invoices,
        OrderRepository $orders,
        IdempotencyService $idempotency
    ) {
        $this->db = $db;
        $this->verifier = $verifier;
        $this->normalizer = $normalizer;
        $this->payments = $payments;
        $this->invoices = $invoices;
        $this->orders = $orders;
        $this->idempotency = $idempotency;
    }

    /**
     * @param array<string, mixed> $headers
     * @return array{applied: bool, reason: string}
     */
    public function handle(string $provider, string $rawBody, array $headers): array
    {
        $verification = $this->verifier->verifyProviderEvent($provider, $rawBody, $headers);

        if (!$verification->ok()) {
            return ['applied' => false, 'reason' => $verification->reason()];
        }

        $decoded = json_decode($rawBody, true);

        if (!is_array($decoded)) {
            return ['applied' => false, 'reason' => 'invalid_payload'];
        }

        $event = $this->normalizer->normalize($provider, $decoded);
        $eventId = $event['eventId'];

        if ($eventId === '') {
            return ['applied' => false, 'reason' => 'missing_event_id'];
        }

        if ($this->idempotency->hasProcessed($eventId)) {
            return ['applied' => false, 'reason' => 'duplicate'];
        }

        $reference = $event['paymentReference'];
        $existing = $reference === '' ? null : $this->payments->findByReference($reference);

        if ($existing !== null && $existing->status === PaymentStatus::PAID && $event['status'] === PaymentStatus::PAID) {
            $this->idempotency->markProcessed($eventId);

            return ['applied' => false, 'reason' => 'already_reconciled'];
        }

        $order = $this->locateOrder($event['amountCents'], $event['currency']);

        if ($order === null) {
            $this->idempotency->markProcessed($eventId);

            return ['applied' => false, 'reason' => 'no_matching_order'];
        }

        $payment = new Payment(
            $this->db->nextId('payment'),
            $order->id,
            $reference,
            $eventId,
            $event['amountCents'],
            $event['currency'],
            $event['status']
        );
        $this->payments->save($payment);

        if ($event['status'] === PaymentStatus::PAID) {
            $invoice = $this->invoices->findByOrder($order->id);

            if ($invoice !== null) {
                $paidCents = 0;

                foreach ($this->payments->findByOrder($order->id) as $p) {
                    if ($p->status === PaymentStatus::PAID) {
                        $paidCents += $p->amountCents;
                    }
                }

                $invoice->paidCents = $paidCents;
                $this->invoices->save($invoice);

                if ($invoice->refundedCents <= 0) {
                    $order->status = PaymentStatus::PAID;
                } elseif ($invoice->refundedCents >= $paidCents) {
                    $order->status = PaymentStatus::REFUNDED;
                } else {
                    $order->status = PaymentStatus::PARTIALLY_REFUNDED;
                }

                $this->orders->save($order);
            }
        } elseif ($event['status'] === PaymentStatus::FAILED) {
            $invoice = $this->invoices->findByOrder($order->id);
            $hasPaid = false;

            foreach ($this->payments->findByOrder($order->id) as $p) {
                if ($p->status === PaymentStatus::PAID) {
                    $hasPaid = true;
                    break;
                }
            }

            if (!$hasPaid && $order->status === PaymentStatus::PENDING) {
                $this->orders->save($order);
            }
        }

        $this->idempotency->markProcessed($eventId);

        return ['applied' => true, 'reason' => $event['status']];
    }

    private function locateOrder(int $amountCents, string $currency): ?\App\Domain\Order
    {
        $pendingMatch = null;
        $anyMatch = null;

        foreach ($this->orders->all() as $order) {
            if ($order->currency !== $currency) {
                continue;
            }

            if ($order->totalCents !== $amountCents) {
                continue;
            }

            if ($order->status === PaymentStatus::PENDING && $pendingMatch === null) {
                $pendingMatch = $order;
            }

            if ($anyMatch === null) {
                $anyMatch = $order;
            }
        }

        return $pendingMatch ?? $anyMatch;
    }
}
