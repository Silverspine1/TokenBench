<?php

declare(strict_types=1);

namespace App\Services;

use App\Domain\RecurringAttempt;
use App\Domain\RecurringSchedule;
use App\Store\Database;
use App\Store\RecurringScheduleRepository;
use DomainException;

/**
 * Drives saved recurring payment schedules. The flow is fully deterministic:
 * a caller passes the current day ($today as YYYY-MM-DD) and the service emits
 * the attempts that are due, advancing each schedule's nextRunAt as it goes.
 * No real gateway is ever contacted.
 */
final class RecurringPaymentService
{
    private Database $db;
    private RecurringScheduleRepository $schedules;

    public function __construct(Database $db, RecurringScheduleRepository $schedules)
    {
        $this->db = $db;
        $this->schedules = $schedules;
    }

    public function createSchedule(
        string $customerId,
        int $amountCents,
        string $currency,
        int $intervalDays,
        string $nextRunAt
    ): RecurringSchedule {
        if ($amountCents <= 0) {
            throw new DomainException('Recurring amount must be positive');
        }

        if ($intervalDays <= 0) {
            throw new DomainException('Interval days must be positive');
        }

        $schedule = new RecurringSchedule(
            $this->db->nextId('rsched'),
            $customerId,
            $amountCents,
            $currency,
            $intervalDays,
            $nextRunAt,
            RecurringSchedule::STATUS_ACTIVE
        );
        $this->schedules->saveSchedule($schedule);

        return $schedule;
    }

    /**
     * Generate the payment attempts due as of $today across every schedule.
     * An active schedule whose nextRunAt is on or before $today produces one
     * attempt and advances nextRunAt by its interval. Inactive schedules are
     * skipped. Deterministic and offline.
     *
     * @return array<int, RecurringAttempt>
     */
    public function generateDueAttempts(string $today): array
    {
        $generated = [];

        foreach ($this->schedules->allSchedules() as $schedule) {
            if (!$schedule->isDueOn($today)) {
                continue;
            }

            $attempt = new RecurringAttempt(
                $this->db->nextId('rattempt'),
                $schedule->id,
                $schedule->customerId,
                $schedule->amountCents,
                $schedule->currency,
                $schedule->nextRunAt,
                RecurringAttempt::STATUS_PENDING
            );
            $this->schedules->saveAttempt($attempt);

            $schedule->advance();
            $this->schedules->saveSchedule($schedule);

            $generated[] = $attempt;
        }

        return $generated;
    }
}
