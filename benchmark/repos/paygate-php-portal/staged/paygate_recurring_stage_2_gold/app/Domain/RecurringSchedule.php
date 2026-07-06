<?php

declare(strict_types=1);

namespace App\Domain;

/**
 * A saved customer instruction to attempt a payment of a fixed amount on a
 * fixed cadence. The schedule is a small state machine: an active schedule
 * advances its nextRunAt each time a due attempt is generated, while an
 * inactive (non-active) schedule produces nothing.
 *
 * Dates are plain YYYY-MM-DD strings so the whole flow is deterministic and
 * never reads the wall clock.
 */
final class RecurringSchedule
{
    public const STATUS_ACTIVE = 'active';
    public const STATUS_INACTIVE = 'inactive';
    public const STATUS_PAUSED = 'paused';

    /** Repeated failures up to this count pause the schedule automatically. */
    public const MAX_FAILURES = 3;

    public string $id;
    public string $customerId;
    public int $amountCents;
    public string $currency;
    public int $intervalDays;
    public string $nextRunAt;
    public string $status;
    public int $failureCount;

    public function __construct(
        string $id,
        string $customerId,
        int $amountCents,
        string $currency,
        int $intervalDays,
        string $nextRunAt,
        string $status = self::STATUS_ACTIVE,
        int $failureCount = 0
    ) {
        $this->id = $id;
        $this->customerId = $customerId;
        $this->amountCents = $amountCents;
        $this->currency = strtoupper(trim($currency));
        $this->intervalDays = $intervalDays;
        $this->nextRunAt = $nextRunAt;
        $this->status = $status;
        $this->failureCount = $failureCount;
    }

    public function isPaused(): bool
    {
        return $this->status === self::STATUS_PAUSED;
    }

    /**
     * Pause the schedule so it stops producing due attempts. Idempotent.
     */
    public function pause(): void
    {
        if ($this->status !== self::STATUS_INACTIVE) {
            $this->status = self::STATUS_PAUSED;
        }
    }

    /**
     * Resume a paused schedule back to active and clear the failure streak.
     * Idempotent for an already-active schedule.
     */
    public function resume(): void
    {
        if ($this->status === self::STATUS_PAUSED) {
            $this->status = self::STATUS_ACTIVE;
            $this->failureCount = 0;
        }
    }

    /**
     * Record a failed attempt against this schedule. Once the failure streak
     * reaches MAX_FAILURES the schedule is paused automatically.
     */
    public function registerFailure(): void
    {
        $this->failureCount++;

        if ($this->failureCount >= self::MAX_FAILURES) {
            $this->pause();
        }
    }

    public function id(): string
    {
        return $this->id;
    }

    public function customerId(): string
    {
        return $this->customerId;
    }

    public function isActive(): bool
    {
        return $this->status === self::STATUS_ACTIVE;
    }

    /**
     * True when an active schedule's next run is on or before the given day.
     */
    public function isDueOn(string $today): bool
    {
        return $this->isActive() && $this->nextRunAt <= $today;
    }

    /**
     * Advance nextRunAt by intervalDays. Pure date math on YYYY-MM-DD strings;
     * no wall-clock access.
     */
    public function advance(): void
    {
        $this->nextRunAt = self::addDays($this->nextRunAt, $this->intervalDays);
    }

    public static function addDays(string $date, int $days): string
    {
        $ts = strtotime($date . ' UTC');
        $ts += $days * 86400;

        return gmdate('Y-m-d', $ts);
    }
}
