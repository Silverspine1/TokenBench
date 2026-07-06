<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\RecurringAttempt;
use App\Domain\RecurringSchedule;

final class RecurringScheduleRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function saveSchedule(RecurringSchedule $schedule): void
    {
        $this->db->recurringSchedules[$schedule->id] = $schedule;
    }

    public function findSchedule(string $id): ?RecurringSchedule
    {
        return $this->db->recurringSchedules[$id] ?? null;
    }

    /**
     * @return array<int, RecurringSchedule>
     */
    public function allSchedules(): array
    {
        return array_values($this->db->recurringSchedules);
    }

    public function saveAttempt(RecurringAttempt $attempt): void
    {
        $this->db->recurringAttempts[$attempt->id] = $attempt;
    }

    /**
     * @return array<int, RecurringAttempt>
     */
    public function attemptsForSchedule(string $scheduleId): array
    {
        $result = [];

        foreach ($this->db->recurringAttempts as $attempt) {
            if ($attempt->scheduleId === $scheduleId) {
                $result[] = $attempt;
            }
        }

        return $result;
    }

    /**
     * @return array<int, RecurringAttempt>
     */
    public function allAttempts(): array
    {
        return array_values($this->db->recurringAttempts);
    }
}
