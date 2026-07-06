<?php

declare(strict_types=1);

namespace App\Store;

final class IdempotencyRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function has(string $eventId): bool
    {
        return isset($this->db->idempotency[$eventId]);
    }

    public function record(string $eventId): void
    {
        $this->db->idempotency[$eventId] = true;
    }
}
