<?php

declare(strict_types=1);

namespace App\Services;

use App\Store\IdempotencyRepository;

final class IdempotencyService
{
    private IdempotencyRepository $repository;

    public function __construct(IdempotencyRepository $repository)
    {
        $this->repository = $repository;
    }

    public function hasProcessed(string $eventId): bool
    {
        return $this->repository->has($eventId);
    }

    public function markProcessed(string $eventId): void
    {
        $this->repository->record($eventId);
    }
}
