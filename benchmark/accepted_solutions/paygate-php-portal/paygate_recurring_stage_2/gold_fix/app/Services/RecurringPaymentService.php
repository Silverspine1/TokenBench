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

    /**
     * Pause a schedule so it stops producing due attempts until resumed.
     */
    public function pauseSchedule(string $scheduleId): RecurringSchedule
    {
        $schedule = $this->requireSchedule($scheduleId);
        $schedule->pause();
        $this->schedules->saveSchedule($schedule);

        return $schedule;
    }

    /**
     * Manually resume a paused schedule, clearing its failure streak so it can
     * produce due attempts again.
     */
    public function resumeSchedule(string $scheduleId): RecurringSchedule
    {
        $schedule = $this->requireSchedule($scheduleId);
        $schedule->resume();
        $this->schedules->saveSchedule($schedule);

        return $schedule;
    }

    /**
     * Mark a generated attempt as failed and record the failure against its
     * schedule. Once a schedule accumulates MAX_FAILURES failures it is paused
     * automatically. Idempotent: failing an already-failed attempt does not
     * increment the schedule's failure count a second time.
     */
    public function markAttemptFailed(string $attemptId): RecurringAttempt
    {
        $attempt = $this->schedules->findAttempt($attemptId);

        if ($attempt === null) {
            throw new DomainException('Unknown recurring attempt: ' . $attemptId);
        }

        if ($attempt->isFailed()) {
            return $attempt;
        }

        $attempt->status = RecurringAttempt::STATUS_FAILED;
        $this->schedules->saveAttempt($attempt);

        $schedule = $this->schedules->findSchedule($attempt->scheduleId);

        if ($schedule !== null) {
            $schedule->registerFailure();
            $this->schedules->saveSchedule($schedule);
        }

        return $attempt;
    }

    /**
     * Retry a failed attempt. Creates a new attempt only when the original is
     * failed and has not already been retried; otherwise returns the existing
     * retry (or the original). This keeps retries idempotent so a charge is
     * never duplicated.
     */
    public function retryAttempt(string $attemptId): RecurringAttempt
    {
        $original = $this->schedules->findAttempt($attemptId);

        if ($original === null) {
            throw new DomainException('Unknown recurring attempt: ' . $attemptId);
        }

        if (!$original->isFailed()) {
            return $original;
        }

        $existingRetry = $this->schedules->retryOf($attemptId);

        if ($existingRetry !== null) {
            return $existingRetry;
        }

        $retry = new RecurringAttempt(
            $this->db->nextId('rattempt'),
            $original->scheduleId,
            $original->customerId,
            $original->amountCents,
            $original->currency,
            $original->runDate,
            RecurringAttempt::STATUS_PENDING,
            $attemptId
        );
        $this->schedules->saveAttempt($retry);

        return $retry;
    }

    private function requireSchedule(string $scheduleId): RecurringSchedule
    {
        $schedule = $this->schedules->findSchedule($scheduleId);

        if ($schedule === null) {
            throw new DomainException('Unknown recurring schedule: ' . $scheduleId);
        }

        return $schedule;
    }
}
