<?php

declare(strict_types=1);

namespace App\Domain;

final class Refund
{
    public string $id;
    public string $paymentId;
    public int $amountCents;

    public function __construct(string $id, string $paymentId, int $amountCents)
    {
        $this->id = $id;
        $this->paymentId = $paymentId;
        $this->amountCents = $amountCents;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function paymentId(): string
    {
        return $this->paymentId;
    }

    public function amountCents(): int
    {
        return $this->amountCents;
    }
}
