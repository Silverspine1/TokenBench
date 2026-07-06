<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\PaymentStatus;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;
use App\Store\PaymentRepository;
use App\Store\RefundRepository;

final class PaymentReportService
{
    private OrderRepository $orders;
    private PaymentRepository $payments;
    private RefundRepository $refunds;
    private InvoiceRepository $invoices;

    public function __construct(
        OrderRepository $orders,
        PaymentRepository $payments,
        RefundRepository $refunds,
        InvoiceRepository $invoices
    ) {
        $this->orders = $orders;
        $this->payments = $payments;
        $this->refunds = $refunds;
        $this->invoices = $invoices;
    }

    /**
     * @return array<int, array{orderId: string, currency: string, totalCents: int, paidCents: int, dueCents: int, status: string}>
     */
    public function report(): array
    {
        $rows = [];

        foreach ($this->orders->all() as $order) {
            $paidCents = 0;
            $refundedCents = 0;

            foreach ($this->payments->findByOrder($order->id) as $payment) {
                if ($payment->status === PaymentStatus::PAID) {
                    $paidCents += $payment->amountCents;
                }

                foreach ($this->refunds->findByPayment($payment->id) as $refund) {
                    $refundedCents += $refund->amountCents;
                }
            }

            $dueCents = (int) (($order->totalCents / 100 - ($paidCents - $refundedCents) / 100) * 100);

            $rows[] = [
                'orderId' => $order->id,
                'currency' => $order->currency,
                'totalCents' => $order->totalCents,
                'paidCents' => $paidCents,
                'dueCents' => $dueCents,
                'status' => $order->status,
            ];
        }

        return $rows;
    }
}
