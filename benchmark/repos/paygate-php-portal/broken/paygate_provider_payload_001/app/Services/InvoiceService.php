<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\PaymentStatus;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;
use App\Store\PaymentRepository;
use App\Store\RefundRepository;

final class InvoiceService
{
    private InvoiceRepository $invoices;
    private PaymentRepository $payments;
    private RefundRepository $refunds;
    private OrderRepository $orders;

    public function __construct(
        InvoiceRepository $invoices,
        PaymentRepository $payments,
        RefundRepository $refunds,
        OrderRepository $orders
    ) {
        $this->invoices = $invoices;
        $this->payments = $payments;
        $this->refunds = $refunds;
        $this->orders = $orders;
    }

    public function recompute(string $orderId): void
    {
        $invoice = $this->invoices->findByOrder($orderId);

        if ($invoice === null) {
            return;
        }

        $paidCents = 0;
        $refundedCents = 0;

        foreach ($this->payments->findByOrder($orderId) as $payment) {
            if ($payment->status === PaymentStatus::PAID) {
                $paidCents += $payment->amountCents;
            }

            foreach ($this->refunds->findByPayment($payment->id) as $refund) {
                $refundedCents += $refund->amountCents;
            }
        }

        $invoice->paidCents = $paidCents;
        $invoice->refundedCents = $refundedCents;
        $this->invoices->save($invoice);

        $order = $this->orders->find($orderId);

        if ($order === null) {
            return;
        }

        $order->status = $this->deriveStatus($paidCents, $refundedCents, $invoice->totalCents);
        $this->orders->save($order);
    }

    private function deriveStatus(int $paidCents, int $refundedCents, int $totalCents): string
    {
        if ($paidCents <= 0) {
            return PaymentStatus::PENDING;
        }

        if ($refundedCents <= 0) {
            return PaymentStatus::PAID;
        }

        if ($refundedCents >= $paidCents) {
            return PaymentStatus::REFUNDED;
        }

        return PaymentStatus::PARTIALLY_REFUNDED;
    }
}
