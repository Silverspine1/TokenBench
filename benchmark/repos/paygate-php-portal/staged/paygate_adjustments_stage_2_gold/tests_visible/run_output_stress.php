<?php

declare(strict_types=1);

// Controlled long-output visible check (V0.8 output_stress). Emits a bounded,
// deterministic block of per-case lines through the public Container flow so the
// harness has a realistic large test-output to measure (for output-compression
// benchmarking). Offline, deterministic, ~140 KB. Always exits 0.
//   php tests_visible/run_output_stress.php

require __DIR__ . '/../app/bootstrap.php';

use App\Domain\Money;
use App\Domain\PaymentStatus;

$CURRENCIES = ['USD', 'ZAR', 'EUR'];
$STATUSES = ['succeeded', 'complete', 'failed', 'pending', 'refunded'];
$CASES = 1800;

$lines = 0;
for ($i = 0; $i < $CASES; $i++) {
    $currency = $CURRENCIES[$i % count($CURRENCIES)];
    $rawStatus = $STATUSES[$i % count($STATUSES)];
    $cents = 1000 + ($i % 500);
    $decimal = Money::fromCents($cents, $currency)->toDecimalString();
    $status = PaymentStatus::normalize($rawStatus);

    printf(
        "case %05d currency=%-3s raw=%-9s status=%-18s cents=%6d amount=%9s :: normalized\n",
        $i,
        $currency,
        $rawStatus,
        $status,
        $cents,
        $decimal
    );
    $lines++;
}

echo "output-stress OK: {$lines} cases normalized\n";
exit(0);
