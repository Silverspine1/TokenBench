<?php

declare(strict_types=1);

// Controlled long-output visible check (V0.8 output_stress). Drives many
// recurring-schedule billing cycles through the public RecurringPaymentService
// and prints one fixed-width line per generated cycle, so the harness has a
// realistic large test-output to measure (for output-compression
// benchmarking). Offline, deterministic, no real gateway. Always exits 0.
//   php tests_visible/run_output_stress.php

require __DIR__ . '/../app/bootstrap.php';

use App\Container;
use App\Domain\RecurringSchedule;

$c = new Container();

// A spread of customers on different fixed cadences, all starting the same day.
$INTERVALS = [1, 7, 14, 30];
$SCHEDULES = 24;

$schedules = [];
for ($s = 0; $s < $SCHEDULES; $s++) {
    $interval = $INTERVALS[$s % count($INTERVALS)];
    $amount = 1000 + (($s * 137) % 9000);
    $schedules[] = $c->recurringService->createSchedule(
        sprintf('cust_%03d', $s),
        $amount,
        'USD',
        $interval,
        '2026-01-01'
    );
}

// Walk a deterministic calendar; on each day generate the due attempts and
// print one line per generated cycle. ~70 days x 24 schedules -> bounded output.
$DAYS = 70;
$cycles = 0;
for ($d = 0; $d < $DAYS; $d++) {
    $today = RecurringSchedule::addDays('2026-01-01', $d);
    $generated = $c->recurringService->generateDueAttempts($today);

    foreach ($generated as $attempt) {
        printf(
            "cycle %05d day=%s schedule=%-9s customer=%-9s amountCents=%6d currency=%-3s runDate=%s status=%-9s :: billed\n",
            $cycles,
            $today,
            $attempt->scheduleId,
            $attempt->customerId,
            $attempt->amountCents,
            $attempt->currency,
            $attempt->runDate,
            $attempt->status
        );
        $cycles++;
    }
}

echo "output-stress OK: {$cycles} recurring cycles generated\n";
exit(0);
