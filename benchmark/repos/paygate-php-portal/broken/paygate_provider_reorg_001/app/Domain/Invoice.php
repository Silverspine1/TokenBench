<?php

declare(strict_types=1);

namespace App\Domain;

final class Invoice
{
    public string $id;
    public string $orderId;
    public int $totalCents;
    public int $paidCents;
    public int $refundedCents;

    public function __construct(
        string $id,
        string $orderId,
        int $totalCents,
        int $paidCents = 0,
        int $refundedCents = 0
    ) {
        $this->id = $id;
        $this->orderId = $orderId;
        $this->totalCents = $totalCents;
        $this->paidCents = $paidCents;
        $this->refundedCents = $refundedCents;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function orderId(): string
    {
        return $this->orderId;
    }

    public function netPaidCents(): int
    {
        return $this->paidCents - $this->refundedCents;
    }

    public function dueCents(): int
    {
        return $this->totalCents - $this->netPaidCents();
    }

    public function isPaid(): bool
    {
        return $this->dueCents() <= 0;
    }
}
