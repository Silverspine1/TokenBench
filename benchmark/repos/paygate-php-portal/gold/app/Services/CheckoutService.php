<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\Cart;
use App\Domain\Invoice;
use App\Domain\Order;
use App\Domain\PaymentStatus;
use App\Store\Database;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;

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
