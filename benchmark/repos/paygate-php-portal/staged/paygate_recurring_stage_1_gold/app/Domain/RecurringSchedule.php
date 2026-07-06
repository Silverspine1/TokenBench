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

    public string $id;
    public string $customerId;
    public int $amountCents;
    public string $currency;
    public int $intervalDays;
    public string $nextRunAt;
    public string $status;

    public function __construct(
        string $id,
        string $customerId,
        int $amountCents,
        string $currency,
        int $intervalDays,
        string $nextRunAt,
        string $status = self::STATUS_ACTIVE
    ) {
        $this->id = $id;
        $this->customerId = $customerId;
        $this->amountCents = $amountCents;
        $this->currency = strtoupper(trim($currency));
        $this->intervalDays = $intervalDays;
        $this->nextRunAt = $nextRunAt;
        $this->status = $status;
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
