<?php

declare(strict_types=1);

namespace App\Payment;

use App\Domain\Money;
use App\Domain\PaymentStatus;
use InvalidArgumentException;

final class GatewayEventNormalizer
{
    /**
     * @param array<string, mixed> $payload
     * @return array{provider: string, eventId: string, paymentReference: string, status: string, amountCents: int, currency: string}
     */
    public function normalize(string $provider, array $payload): array
    {
        $canonicalProvider = strtolower(trim($provider));

        switch ($canonicalProvider) {
            case 'stripe':
                return $this->normalizeStripe($payload);
            case 'payfast':
                return $this->normalizePayFast($payload);
            default:
                throw new InvalidArgumentException('Unknown provider: ' . $provider);
        }
    }

    /**
     * @param array<string, mixed> $payload
     * @return array{provider: string, eventId: string, paymentReference: string, status: string, amountCents: int, currency: string}
     */
    private function normalizeStripe(array $payload): array
    {
        if (isset($payload['data']['object'])) {
            $object = $payload['data']['object'];
            $eventId = (string) ($payload['id'] ?? '');
            $paymentReference = (string) ($object['id'] ?? '');
            $amountCents = (int) ($object['amount'] ?? 0);
            $currency = (string) ($object['currency'] ?? '');
            $status = (string) ($object['status'] ?? '');
        } else {
            $eventId = (string) ($payload['event_id'] ?? '');
            $paymentReference = (string) ($payload['payment_ref'] ?? '');
            $amountCents = (int) ($payload['amount_cents'] ?? 0);
            $currency = (string) ($payload['currency'] ?? '');
            $status = (string) ($payload['status'] ?? '');
        }

        return [
            'provider' => 'stripe',
            'eventId' => $eventId,
            'paymentReference' => $paymentReference,
            'status' => PaymentStatus::normalize($status),
            'amountCents' => $amountCents,
            'currency' => strtoupper(trim($currency)),
        ];
    }

    /**
     * @param array<string, mixed> $payload
     * @return array{provider: string, eventId: string, paymentReference: string, status: string, amountCents: int, currency: string}
     */
    private function normalizePayFast(array $payload): array
    {
        if (isset($payload['m_payment_id']) || isset($payload['pf_payment_id'])) {
            $eventId = (string) ($payload['m_payment_id'] ?? '');
            $paymentReference = (string) ($payload['pf_payment_id'] ?? '');
            $amountString = (string) ($payload['amount_gross'] ?? '0');
            $currency = (string) ($payload['currency_code'] ?? '');
            $status = (string) ($payload['payment_status'] ?? '');
        } else {
            $eventId = (string) ($payload['payment_id'] ?? '');
            $paymentReference = (string) ($payload['reference'] ?? '');
            $amountString = (string) ($payload['amount'] ?? '0');
            $currency = (string) ($payload['currency'] ?? '');
            $status = (string) ($payload['status'] ?? '');
        }

        $amountCents = Money::fromDecimalString($amountString, $currency === '' ? 'ZAR' : $currency)->cents();

        return [
            'provider' => 'payfast',
            'eventId' => $eventId,
            'paymentReference' => $paymentReference,
            'status' => PaymentStatus::normalize($status),
            'amountCents' => $amountCents,
            'currency' => strtoupper(trim($currency)),
        ];
    }
}
