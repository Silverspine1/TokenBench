<?php

declare(strict_types=1);

namespace App\Payment;

interface GatewayInterface
{
    public function name(): string;

    /**
     * @param array<string, mixed> $headers
     */
    public function verifySignature(string $rawBody, array $headers): bool;
}
