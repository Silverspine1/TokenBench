<?php

declare(strict_types=1);

require __DIR__ . '/../app/bootstrap.php';

use App\Payment\PayFastMockGateway;
use App\Payment\StripeMockGateway;

$fixturesDir = __DIR__ . '/../fixtures';

$carts = [
    [
        'id' => 'cart_alpha',
        'currency' => 'USD',
        'items' => [
            ['sku' => 'SKU-1', 'quantity' => 2, 'unitCents' => 500],
            ['sku' => 'SKU-2', 'quantity' => 1, 'unitCents' => 1234],
        ],
    ],
    [
        'id' => 'cart_beta',
        'currency' => 'ZAR',
        'items' => [
            ['sku' => 'SKU-9', 'quantity' => 1, 'unitCents' => 9900],
        ],
    ],
];

file_put_contents(
    $fixturesDir . '/carts.json',
    json_encode($carts, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR) . "\n"
);

$bodies = [
    'stripe_new_paid' => [
        'provider' => 'stripe',
        'payload' => [
            'id' => 'evt_stripe_new_1',
            'data' => [
                'object' => [
                    'id' => 'pi_stripe_1',
                    'amount' => 2234,
                    'currency' => 'usd',
                    'status' => 'succeeded',
                ],
            ],
        ],
    ],
    'stripe_old_paid' => [
        'provider' => 'stripe',
        'payload' => [
            'event_id' => 'evt_stripe_old_1',
            'payment_ref' => 'pi_stripe_2',
            'amount_cents' => 2234,
            'currency' => 'USD',
            'status' => 'Paid',
        ],
    ],
    'payfast_new_paid' => [
        'provider' => 'payfast',
        'payload' => [
            'm_payment_id' => 'mpf_new_1',
            'pf_payment_id' => 'pf_ref_1',
            'amount_gross' => '99.00',
            'currency_code' => 'ZAR',
            'payment_status' => 'COMPLETE',
        ],
    ],
    'payfast_old_paid' => [
        'provider' => 'payfast',
        'payload' => [
            'payment_id' => 'mpf_old_1',
            'reference' => 'pf_ref_2',
            'amount' => '99.00',
            'currency' => 'ZAR',
            'status' => 'completed',
        ],
    ],
    'stripe_failed' => [
        'provider' => 'stripe',
        'payload' => [
            'id' => 'evt_stripe_new_failed',
            'data' => [
                'object' => [
                    'id' => 'pi_stripe_failed',
                    'amount' => 2234,
                    'currency' => 'usd',
                    'status' => 'declined',
                ],
            ],
        ],
    ],
];

$events = [];

foreach ($bodies as $name => $entry) {
    $rawBody = json_encode($entry['payload'], JSON_THROW_ON_ERROR);

    if ($entry['provider'] === 'stripe') {
        $signature = StripeMockGateway::sign($rawBody);
        $header = 'Stripe-Signature';
    } else {
        $signature = PayFastMockGateway::sign($rawBody);
        $header = 'X-PayFast-Signature';
    }

    $events[$name] = [
        'provider' => $entry['provider'],
        'rawBody' => $rawBody,
        'headers' => [$header => $signature],
    ];
}

file_put_contents(
    $fixturesDir . '/webhook_events.json',
    json_encode($events, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR) . "\n"
);

$gatewayResponses = [
    'stripe' => ['name' => 'stripe', 'signatureHeader' => 'Stripe-Signature'],
    'payfast' => ['name' => 'payfast', 'signatureHeader' => 'X-PayFast-Signature'],
];

file_put_contents(
    $fixturesDir . '/gateway_responses.json',
    json_encode($gatewayResponses, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR) . "\n"
);

$adminReports = [
    [
        'orderId' => 'order_1',
        'currency' => 'USD',
        'totalCents' => 2234,
        'paidCents' => 2234,
        'dueCents' => 0,
        'status' => 'paid',
    ],
];

file_put_contents(
    $fixturesDir . '/admin_reports.json',
    json_encode($adminReports, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR) . "\n"
);

echo "fixtures generated\n";
