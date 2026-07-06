<?php

declare(strict_types=1);

// Legacy import dump (a). Webhook signature verification ended up here, away
// from the gateways it coordinates. Loaded explicitly by bootstrap.

namespace App\Payment;

use App\Domain\VerificationResult;

final class WebhookVerifier
{
    /** @var array<string, GatewayInterface> */
    private array $gatewaysByName;

    /**
     * @param array<string, GatewayInterface> $gatewaysByName
     */
    public function __construct(array $gatewaysByName)
    {
        $this->gatewaysByName = [];

        foreach ($gatewaysByName as $name => $gateway) {
            $this->gatewaysByName[strtolower((string) $name)] = $gateway;
        }
    }

    /**
     * @param array<string, mixed> $headers
     */
    public function verifyProviderEvent(string $provider, string $rawBody, array $headers): VerificationResult
    {
        $key = strtolower(trim($provider));

        if (!isset($this->gatewaysByName[$key])) {
            return VerificationResult::fail('unknown_provider');
        }

        $gateway = $this->gatewaysByName[$key];

        if (!$gateway->verifySignature($rawBody, $headers)) {
            return VerificationResult::fail('invalid_signature');
        }

        return VerificationResult::pass();
    }
}
