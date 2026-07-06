<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\Refund;

final class RefundRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function save(Refund $refund): void
    {
        $this->db->refunds[$refund->id] = $refund;
    }

    public function find(string $id): ?Refund
    {
        return $this->db->refunds[$id] ?? null;
    }

    /**
     * @return array<int, Refund>
     */
    public function findByPayment(string $paymentId): array
    {
        $result = [];

        foreach ($this->db->refunds as $refund) {
            if ($refund->paymentId === $paymentId) {
                $result[] = $refund;
            }
        }

        return $result;
    }

    /**
     * @return array<int, Refund>
     */
    public function all(): array
    {
        return array_values($this->db->refunds);
    }
}
