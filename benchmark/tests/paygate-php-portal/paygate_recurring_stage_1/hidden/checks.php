<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\RecurringSchedule;

$results = [];

// --- daily_schedule: an active daily schedule due today emits one attempt ---
$c = new Container();
$sched = $c->recurringService->createSchedule('cust_a', 1500, 'USD', 1, '2026-01-01');
$gen = $c->recurringService->generateDueAttempts('2026-01-01');
$results['daily_schedule'] =
    count($gen) === 1
    && $gen[0]->scheduleId === $sched->id
    && $gen[0]->amountCents === 1500
    && $gen[0]->currency === 'USD'
    && $gen[0]->runDate === '2026-01-01';

// --- monthly_like_interval: a fixed 30-day interval advances by 30 days ---
$c2 = new Container();
$m = $c2->recurringService->createSchedule('cust_b', 9900, 'USD', 30, '2026-03-01');
$c2->recurringService->generateDueAttempts('2026-03-10');
$results['monthly_like_interval'] = $m->nextRunAt === '2026-03-31';

// --- inactive_schedule_ignored: a non-active schedule produces nothing ---
$c3 = new Container();
$ina = $c3->recurringService->createSchedule('cust_c', 1000, 'USD', 1, '2026-01-01');
$ina->status = RecurringSchedule::STATUS_INACTIVE;
$c3->recurringSchedules->saveSchedule($ina);
$genIna = $c3->recurringService->generateDueAttempts('2026-12-31');
$results['inactive_schedule_ignored'] = count($genIna) === 0;

// --- next_run_at_advances_after_generation: generating advances nextRunAt and
//     a second call on the same day yields nothing ---
$c4 = new Container();
$adv = $c4->recurringService->createSchedule('cust_d', 2000, 'USD', 7, '2026-05-01');
$first = $c4->recurringService->generateDueAttempts('2026-05-01');
$advancedTo = $adv->nextRunAt;
$second = $c4->recurringService->generateDueAttempts('2026-05-01');
$results['next_run_at_advances_after_generation'] =
    count($first) === 1
    && $advancedTo === '2026-05-08'
    && count($second) === 0;

// --- one_time_checkout_unaffected: ordinary checkout reuse still holds ---
$c5 = new Container();
$cart = new Cart('cart_z', 'USD', [['sku' => 'Z', 'quantity' => 1, 'unitCents' => 2500]]);
$o1 = $c5->checkout->checkout('sess_z', $cart);
$o2 = $c5->checkout->checkout('sess_z', $cart);
$results['one_time_checkout_unaffected'] =
    $o1->id === $o2->id && count($c5->invoices->all()) === 1;

echo json_encode($results);
exit(0);
