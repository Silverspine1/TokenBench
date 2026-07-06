<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\PaymentStatus;
use App\Domain\Refund;
use App\Store\Database;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;
use App\Store\PaymentRepository;
use App\Store\RefundRepository;
use DomainException;

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

        $orderPayments = $this->payments->findByOrder($orderId);
        $primary = $orderPayments[0] ?? null;

        if ($primary !== null) {
            foreach ($this->refunds->findByPayment($primary->id) as $refund) {
                $refundedCents += $refund->amountCents;
            }
        }

        $invoice->refundedCents = $refundedCents;
        $this->invoices->save($invoice);
    }
}
