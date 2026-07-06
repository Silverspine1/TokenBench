<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\Order;

final class OrderRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function save(Order $order): void
    {
        $this->db->orders[$order->id] = $order;
    }

    public function find(string $id): ?Order
    {
        return $this->db->orders[$id] ?? null;
    }

    /**
     * @return array<int, Order>
     */
    public function all(): array
    {
        return array_values($this->db->orders);
    }
}
