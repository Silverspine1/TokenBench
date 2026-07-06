<?php

declare(strict_types=1);

namespace App\Domain;

final class VerificationResult
{
    private bool $ok;
    private string $reason;

    private function __construct(bool $ok, string $reason)
    {
        $this->ok = $ok;
        $this->reason = $reason;
    }

    public function ok(): bool
    {
        return $this->ok;
    }

    public function reason(): string
    {
        return $this->reason;
    }

    public static function pass(): self
    {
        return new self(true, '');
    }

    public static function fail(string $reason): self
    {
        return new self(false, $reason);
    }
}
