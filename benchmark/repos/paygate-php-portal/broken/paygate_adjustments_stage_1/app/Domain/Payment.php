<?php

declare(strict_types=1);

namespace App\Domain;

final class Payment
{
    public string $id;
    public string $orderId;
    public string $paymentReference;
    public string $eventId;
    public int $amountCents;
    public string $currency;
    public string $status;

    public function __construct(
        string $id,
        string $orderId,
        string $paymentReference,
        string $eventId,
        int $amountCents,
        string $currency,
        string $status
    ) {
        $this->id = $id;
        $this->orderId = $orderId;
        $this->paymentReference = $paymentReference;
        $this->eventId = $eventId;
        $this->amountCents = $amountCents;
        $this->currency = strtoupper(trim($currency));
        $this->status = $status;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function orderId(): string
    {
        return $this->orderId;
    }

    public function paymentReference(): string
    {
        return $this->paymentReference;
    }

    public function eventId(): string
    {
        return $this->eventId;
    }

    public function amountCents(): int
    {
        return $this->amountCents;
    }

    public function currency(): string
    {
        return $this->currency;
    }

    public function status(): string
    {
        return $this->status;
    }
}
