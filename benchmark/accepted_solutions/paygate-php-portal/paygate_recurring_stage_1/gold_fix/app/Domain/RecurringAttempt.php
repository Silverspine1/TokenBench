<?php

declare(strict_types=1);

namespace App\Domain;

/**
 * One generated payment attempt produced by a recurring schedule on a given
 * run date. Deterministic: no gateway call is made; the attempt simply records
 * that the schedule was due and what would be charged.
 */
final class RecurringAttempt
{
    public const STATUS_PENDING = 'pending';
    public const STATUS_SUCCEEDED = 'succeeded';
    public const STATUS_FAILED = 'failed';

    public string $id;
    public string $scheduleId;
    public string $customerId;
    public int $amountCents;
    public string $currency;
    public string $runDate;
    public string $status;

    public function __construct(
        string $id,
        string $scheduleId,
        string $customerId,
        int $amountCents,
        string $currency,
        string $runDate,
        string $status = self::STATUS_PENDING
    ) {
        $this->id = $id;
        $this->scheduleId = $scheduleId;
        $this->customerId = $customerId;
        $this->amountCents = $amountCents;
        $this->currency = strtoupper(trim($currency));
        $this->runDate = $runDate;
        $this->status = $status;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function scheduleId(): string
    {
        return $this->scheduleId;
    }
}
