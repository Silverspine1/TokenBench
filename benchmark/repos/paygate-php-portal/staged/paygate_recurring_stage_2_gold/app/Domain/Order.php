<?php

declare(strict_types=1);

namespace App\Domain;

final class Order
{
    public string $id;
    public string $cartId;
    public string $currency;
    public int $totalCents;
    public string $status;

    public function __construct(
        string $id,
        string $cartId,
        string $currency,
        int $totalCents,
        string $status = PaymentStatus::PENDING
    ) {
        $this->id = $id;
        $this->cartId = $cartId;
        $this->currency = strtoupper(trim($currency));
        $this->totalCents = $totalCents;
        $this->status = $status;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function cartId(): string
    {
        return $this->cartId;
    }

    public function currency(): string
    {
        return $this->currency;
    }

    public function totalCents(): int
    {
        return $this->totalCents;
    }

    public function status(): string
    {
        return $this->status;
    }
}
