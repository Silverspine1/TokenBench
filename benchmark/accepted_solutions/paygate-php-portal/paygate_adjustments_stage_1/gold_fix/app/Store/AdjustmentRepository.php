<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\Adjustment;

final class AdjustmentRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function save(Adjustment $adjustment): void
    {
        $this->db->adjustments[$adjustment->id] = $adjustment;
    }

    public function find(string $id): ?Adjustment
    {
        return $this->db->adjustments[$id] ?? null;
    }

    /**
     * @return array<int, Adjustment>
     */
    public function findByOrder(string $orderId): array
    {
        $result = [];

        foreach ($this->db->adjustments as $adjustment) {
            if ($adjustment->orderId === $orderId) {
                $result[] = $adjustment;
            }
        }

        return $result;
    }

    /**
     * @return array<int, Adjustment>
     */
    public function all(): array
    {
        return array_values($this->db->adjustments);
    }
}
