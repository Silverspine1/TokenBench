<?php

declare(strict_types=1);

// Flattened payment flow. Checkout orchestration, provider notification
// (webhook) handling, and refund handling were bundled into this single
// catch-all file during a legacy import. These classes sit off the PSR-4 path,
// so the autoloader cannot find them; app/bootstrap.php loads this file
// explicitly until the flow is reorganized into per-responsibility services.

namespace App\Services {

    use App\Domain\Cart;
    use App\Domain\Invoice;
    use App\Domain\Order;
    use App\Domain\Payment;
    use App\Domain\PaymentStatus;
    use App\Domain\Refund;
    use App\Payment\GatewayEventNormalizer;
    use App\Payment\WebhookVerifier;
    use App\Store\Database;
    use App\Store\InvoiceRepository;
    use App\Store\OrderRepository;
    use App\Store\PaymentRepository;
    use App\Store\RefundRepository;
    use DomainException;

    final class CheckoutService
    {
        private Database $db;
        private OrderRepository $orders;
        private InvoiceRepository $invoices;

        public function __construct(Database $db, OrderRepository $orders, InvoiceRepository $invoices)
        {
            $this->db = $db;
            $this->orders = $orders;
            $this->invoices = $invoices;
        }

        public function checkout(string $sessionId, Cart $cart): Order
        {
            $fingerprint = $cart->fingerprint();

            foreach ($this->db->sessionOrders[$sessionId] ?? [] as $orderId) {
                $order = $this->orders->find($orderId);

                if ($order === null) {
                    continue;
                }

                if ($order->status !== PaymentStatus::PENDING) {
                    continue;
                }

                if (($this->db->orderFingerprints[$orderId] ?? null) === $fingerprint) {
                    return $order;
                }
            }

            $orderId = $this->db->nextId('order');
            $order = new Order(
                $orderId,
                $cart->id(),
                $cart->currency(),
                $cart->itemsTotalCents(),
                PaymentStatus::PENDING
            );
            $this->orders->save($order);

            $invoice = new Invoice(
                $this->db->nextId('invoice'),
                $orderId,
                $cart->itemsTotalCents(),
                0,
                0
            );
            $this->invoices->save($invoice);

            $this->db->sessionOrders[$sessionId][] = $orderId;
            $this->db->orderFingerprints[$orderId] = $fingerprint;

            return $order;
        }
    }

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

    final class RefundService
    {
        private Database $db;
        private PaymentRepository $payments;
        private RefundRepository $refunds;
        private InvoiceRepository $invoices;
        private OrderRepository $orders;

        public function __construct(
            Database $db,
            PaymentRepository $payments,
            RefundRepository $refunds,
            InvoiceRepository $invoices,
            OrderRepository $orders
        ) {
            $this->db = $db;
            $this->payments = $payments;
            $this->refunds = $refunds;
            $this->invoices = $invoices;
            $this->orders = $orders;
        }

        public function refund(string $paymentId, int $amountCents): Refund
        {
            if ($amountCents <= 0) {
                throw new DomainException('Refund amount must be positive');
            }

            $payment = $this->payments->find($paymentId);

            if ($payment === null) {
                throw new DomainException('Unknown payment: ' . $paymentId);
            }

            $alreadyRefunded = 0;

            foreach ($this->refunds->findByPayment($paymentId) as $existing) {
                $alreadyRefunded += $existing->amountCents;
            }

            if ($alreadyRefunded + $amountCents > $payment->amountCents) {
                throw new DomainException('Refund exceeds paid amount');
            }

            $refund = new Refund(
                $this->db->nextId('refund'),
                $paymentId,
                $amountCents
            );
            $this->refunds->save($refund);

            $this->applyToInvoice($payment->orderId);

            return $refund;
        }

        private function applyToInvoice(string $orderId): void
        {
            $invoice = $this->invoices->findByOrder($orderId);

            if ($invoice === null) {
                return;
            }

            $refundedCents = 0;

            foreach ($this->payments->findByOrder($orderId) as $payment) {
                foreach ($this->refunds->findByPayment($payment->id) as $refund) {
                    $refundedCents += $refund->amountCents;
                }
            }

            $invoice->refundedCents = $refundedCents;
            $this->invoices->save($invoice);

            $order = $this->orders->find($orderId);

            if ($order === null) {
                return;
            }

            if ($invoice->paidCents <= 0) {
                $order->status = PaymentStatus::PENDING;
            } elseif ($refundedCents <= 0) {
                $order->status = PaymentStatus::PAID;
            } elseif ($refundedCents >= $invoice->paidCents) {
                $order->status = PaymentStatus::REFUNDED;
            } else {
                $order->status = PaymentStatus::PARTIALLY_REFUNDED;
            }

            $this->orders->save($order);
        }
    }
}
