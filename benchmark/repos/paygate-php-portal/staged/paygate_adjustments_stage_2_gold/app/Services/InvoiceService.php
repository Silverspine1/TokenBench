<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\PaymentStatus;
use App\Store\AdjustmentRepository;
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
    private AdjustmentRepository $adjustments;

    public function __construct(
        InvoiceRepository $invoices,
        PaymentRepository $payments,
        RefundRepository $refunds,
        OrderRepository $orders,
        AdjustmentRepository $adjustments
    ) {
        $this->invoices = $invoices;
        $this->payments = $payments;
        $this->refunds = $refunds;
        $this->orders = $orders;
        $this->adjustments = $adjustments;
    }

    /**
     * Adjustment-aware finance summary, one row per invoice.
     *
     * Each row reports the public fields {orderId, grossCents, adjustmentsCents,
     * paidCents, dueCents}. The due amount is folded from a list of signed
     * components so the summary always reconciles:
     *
     *     grossCents + adjustmentsCents - paidCents === dueCents
     *
     * ``paidCents`` is the net amount treated as paid: gross payments minus any
     * refunds. Refunds are folded in as one more signed component of net paid,
     * so a refund lowers net paid and raises the amount due, without changing
     * these public fields.
     *
     * @return array<int, array{orderId: string, grossCents: int, adjustmentsCents: int, paidCents: int, dueCents: int}>
     */
    public function summary(): array
    {
        $rows = [];

        foreach ($this->invoices->all() as $invoice) {
            $grossCents = $invoice->totalCents;
            $adjustmentsCents = $this->adjustmentsTotal($invoice->orderId);

            // Net paid folds gross payments and refunds as signed components.
            $paidComponents = [
                'payments' => $invoice->paidCents,
                'refunds' => -$invoice->refundedCents,
            ];
            $paidCents = array_sum($paidComponents);

            // Signed components of the outstanding balance. Each entry is
            // (label, signedCents); their sum is what the customer still owes.
            $components = [
                'gross' => $grossCents,
                'adjustments' => $adjustmentsCents,
                'paid' => -$paidCents,
            ];

            $dueCents = array_sum($components);

            $rows[] = [
                'orderId' => $invoice->orderId,
                'grossCents' => $grossCents,
                'adjustmentsCents' => $adjustmentsCents,
                'paidCents' => $paidCents,
                'dueCents' => $dueCents,
            ];
        }

        return $rows;
    }

    private function adjustmentsTotal(string $orderId): int
    {
        $total = 0;

        foreach ($this->adjustments->findByOrder($orderId) as $adjustment) {
            $total += $adjustment->amountCents;
        }

        return $total;
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
