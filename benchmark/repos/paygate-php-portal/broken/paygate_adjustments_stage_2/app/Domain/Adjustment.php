<?php

declare(strict_types=1);

namespace App\Domain;

/**
 * A manual, signed adjustment applied to an order after checkout.
 *
 * ``amountCents`` is signed: a positive value is a surcharge that raises the
 * amount owed, a negative value is a discount that lowers it. Adjustments are a
 * general signed-amount ledger component, independent of payments and refunds.
 */
final class Adjustment
{
    public string $id;
    public string $orderId;
    public int $amountCents;
    public string $reason;
    public string $createdAt;

    public function __construct(
        string $id,
        string $orderId,
        int $amountCents,
        string $reason,
        string $createdAt
    ) {
        $this->id = $id;
        $this->orderId = $orderId;
        $this->amountCents = $amountCents;
        $this->reason = $reason;
        $this->createdAt = $createdAt;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function orderId(): string
    {
        return $this->orderId;
    }

    public function amountCents(): int
    {
        return $this->amountCents;
    }

    public function reason(): string
    {
        return $this->reason;
    }

    public function createdAt(): string
    {
        return $this->createdAt;
    }
}
