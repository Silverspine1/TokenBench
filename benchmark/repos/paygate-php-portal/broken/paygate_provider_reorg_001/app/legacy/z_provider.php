<?php

declare(strict_types=1);

// Legacy import dump. Several provider concerns were flattened into this single
// file during a migration. The contract, the Stripe-like gateway, and the
// PayFast-like gateway all live here together. Loaded explicitly by bootstrap
// because it does not sit at a PSR-4 path the autoloader can resolve.

namespace App\Payment;

interface GatewayInterface
{
    public function name(): string;

    /**
     * @param array<string, mixed> $headers
     */
    public function verifySignature(string $rawBody, array $headers): bool;
}

final class StripeMockGateway implements GatewayInterface
{
    private const SECRET = 'stripe_mock_shared_secret_v1';
    private const SIGNATURE_HEADER = 'Stripe-Signature';

    public function name(): string
    {
        return 'stripe';
    }

    public function verifySignature(string $rawBody, array $headers): bool
    {
        $provided = self::headerValue($headers, self::SIGNATURE_HEADER);

        if ($provided === null) {
            return false;
        }

        return hash_equals(self::sign($rawBody), $provided);
    }

    public static function sign(string $rawBody): string
    {
        return hash_hmac('sha256', $rawBody, self::SECRET);
    }

    /**
     * @param array<string, mixed> $headers
     */
    private static function headerValue(array $headers, string $name): ?string
    {
        $target = strtolower($name);

        foreach ($headers as $key => $value) {
            if (strtolower((string) $key) === $target) {
                return is_array($value) ? (string) reset($value) : (string) $value;
            }
        }

        return null;
    }
}

final class PayFastMockGateway implements GatewayInterface
{
    private const SECRET = 'payfast_mock_shared_secret_v1';
    private const SIGNATURE_HEADER = 'X-PayFast-Signature';

    public function name(): string
    {
        return 'payfast';
    }

    public function verifySignature(string $rawBody, array $headers): bool
    {
        $provided = self::headerValue($headers, self::SIGNATURE_HEADER);

        if ($provided === null) {
            return false;
        }

        return hash_equals(self::sign($rawBody), $provided);
    }

    public static function sign(string $rawBody): string
    {
        return hash_hmac('sha256', $rawBody, self::SECRET);
    }

    /**
     * @param array<string, mixed> $headers
     */
    private static function headerValue(array $headers, string $name): ?string
    {
        $target = strtolower($name);

        foreach ($headers as $key => $value) {
            if (strtolower((string) $key) === $target) {
                return is_array($value) ? (string) reset($value) : (string) $value;
            }
        }

        return null;
    }
}
