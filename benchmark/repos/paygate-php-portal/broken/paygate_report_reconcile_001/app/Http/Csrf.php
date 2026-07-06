<?php

declare(strict_types=1);

namespace App\Http;

final class Csrf
{
    private string $seed;

    public function __construct(string $seed = 'paygate_csrf_seed_v1')
    {
        $this->seed = $seed;
    }

    public function generate(string $sessionId): string
    {
        return hash_hmac('sha256', $sessionId, $this->seed);
    }

    public function validate(string $sessionId, string $token): bool
    {
        return hash_equals($this->generate($sessionId), $token);
    }
}
