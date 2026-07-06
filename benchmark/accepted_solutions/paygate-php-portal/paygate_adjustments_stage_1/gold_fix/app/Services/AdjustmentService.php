<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\Adjustment;
use App\Store\AdjustmentRepository;
use App\Store\Database;
use App\Store\OrderRepository;
use DomainException;

final class AdjustmentService
{
    private Database $db;
    private AdjustmentRepository $adjustments;
    private OrderRepository $orders;

    public function __construct(
        Database $db,
        AdjustmentRepository $adjustments,
        OrderRepository $orders
    ) {
        $this->db = $db;
        $this->adjustments = $adjustments;
        $this->orders = $orders;
    }

    /**
     * Record a signed manual adjustment against an order. A positive amount is a
     * surcharge, a negative amount is a discount. Zero is not a meaningful
     * adjustment and is rejected.
     */
    public function add(string $orderId, int $amountCents, string $reason): Adjustment
    {
        if ($amountCents === 0) {
            throw new DomainException('Adjustment amount must be non-zero');
        }

        if ($this->orders->find($orderId) === null) {
            throw new DomainException('Unknown order: ' . $orderId);
        }

        $adjustment = new Adjustment(
            $this->db->nextId('adj'),
            $orderId,
            $amountCents,
            $reason,
            date('c')
        );
        $this->adjustments->save($adjustment);

        return $adjustment;
    }

    /**
     * Net signed total of all adjustments recorded against an order.
     */
    public function totalForOrder(string $orderId): int
    {
        $total = 0;

        foreach ($this->adjustments->findByOrder($orderId) as $adjustment) {
            $total += $adjustment->amountCents;
        }

        return $total;
    }
}
