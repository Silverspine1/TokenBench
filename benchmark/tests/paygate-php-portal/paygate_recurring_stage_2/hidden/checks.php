<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\RecurringSchedule;

$results = [];

// --- pause_prevents_due_attempt: a paused schedule produces nothing ---
$c1 = new Container();
$s1 = $c1->recurringService->createSchedule('cust_a', 1500, 'USD', 1, '2026-01-01');
$c1->recurringService->pauseSchedule($s1->id);
$paused = $c1->recurringService->generateDueAttempts('2026-01-10');
$results['pause_prevents_due_attempt'] = count($paused) === 0;

// --- resume_restores_due_attempt: resuming makes it due again ---
$c2 = new Container();
$s2 = $c2->recurringService->createSchedule('cust_b', 1500, 'USD', 1, '2026-01-01');
$c2->recurringService->pauseSchedule($s2->id);
$c2->recurringService->resumeSchedule($s2->id);
$resumed = $c2->recurringService->generateDueAttempts('2026-01-10');
$results['resume_restores_due_attempt'] = count($resumed) === 1;

// --- failed_attempt_increments_failure_count ---
$c3 = new Container();
$s3 = $c3->recurringService->createSchedule('cust_c', 2000, 'USD', 1, '2026-02-01');
$g3 = $c3->recurringService->generateDueAttempts('2026-02-01');
$c3->recurringService->markAttemptFailed($g3[0]->id);
$s3After = $c3->recurringSchedules->findSchedule($s3->id);
$results['failed_attempt_increments_failure_count'] = $s3After->failureCount === 1;

// --- retry_is_idempotent: retrying a failed attempt twice yields one retry ---
$c4 = new Container();
$s4 = $c4->recurringService->createSchedule('cust_d', 2000, 'USD', 1, '2026-02-01');
$g4 = $c4->recurringService->generateDueAttempts('2026-02-01');
$c4->recurringService->markAttemptFailed($g4[0]->id);
$beforeCount = count($c4->recurringSchedules->allAttempts());
$r1 = $c4->recurringService->retryAttempt($g4[0]->id);
$r2 = $c4->recurringService->retryAttempt($g4[0]->id);
$afterCount = count($c4->recurringSchedules->allAttempts());
$results['retry_is_idempotent'] =
    $r1->id === $r2->id
    && ($afterCount - $beforeCount) === 1;

// --- three_failures_pause_schedule: 3 failures auto-pause the schedule ---
$c5 = new Container();
$s5 = $c5->recurringService->createSchedule('cust_e', 1000, 'USD', 1, '2026-04-01');
for ($d = 1; $d <= 3; $d++) {
    $day = sprintf('2026-04-%02d', $d);
    $att = $c5->recurringService->generateDueAttempts($day);
    if (count($att) === 1) {
        $c5->recurringService->markAttemptFailed($att[0]->id);
    }
}
$s5After = $c5->recurringSchedules->findSchedule($s5->id);
$results['three_failures_pause_schedule'] =
    $s5After->isPaused() && $s5After->failureCount >= 3;

// --- stage1_schedule_behavior_unchanged: base daily-due + advance still holds ---
$c6 = new Container();
$s6 = $c6->recurringService->createSchedule('cust_f', 1500, 'USD', 30, '2026-05-01');
$g6 = $c6->recurringService->generateDueAttempts('2026-05-01');
$again = $c6->recurringService->generateDueAttempts('2026-05-01');
$results['stage1_schedule_behavior_unchanged'] =
    count($g6) === 1
    && $g6[0]->amountCents === 1500
    && $s6->nextRunAt === '2026-05-31'
    && count($again) === 0;

echo json_encode($results);
exit(0);
