<?php

declare(strict_types=1);

namespace App\Payment;

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

        $expected = self::sign($rawBody);

        return hash_equals($expected, $provided);
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
