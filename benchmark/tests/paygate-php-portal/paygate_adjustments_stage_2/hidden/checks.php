<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Payment\StripeMockGateway;

/**
 * Fresh container with one order of $total cents, paid in full.
 *
 * @return array{c: Container, orderId: string, paymentId: string}
 */
function paidOrder(int $total, string $tag): array
{
    $c = new Container();
    $cart = new Cart('cart_' . $tag, 'USD', [
        ['sku' => $tag, 'quantity' => 1, 'unitCents' => $total],
    ]);
    $order = $c->checkout->checkout('sess_' . $tag, $cart);

    $body = json_encode([
        'id' => 'evt_' . $tag,
        'data' => ['object' => [
            'id' => 'pi_' . $tag,
            'amount' => $total,
            'currency' => 'usd',
            'status' => 'succeeded',
        ]],
    ], JSON_THROW_ON_ERROR);
    $headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
    $c->webhookService->handle('stripe', $body, $headers);

    $payment = $c->payments->findByReference('pi_' . $tag);

    return ['c' => $c, 'orderId' => $order->id, 'paymentId' => $payment->id];
}

/** Locate the summary row for an order, or null. */
function rowFor(Container $c, string $orderId): ?array
{
    foreach ($c->invoiceService->summary() as $row) {
        if (($row['orderId'] ?? null) === $orderId) {
            return $row;
        }
    }

    return null;
}

$results = [
    'refund_after_positive_adjustment' => false,
    'refund_after_negative_adjustment' => false,
    'partial_refund' => false,
    'full_refund' => false,
    'adjustment_plus_refund_reconciliation' => false,
    'stage1_public_fields_unchanged' => false,
];

// --- refund_after_positive_adjustment ---
// gross 5000, +700 surcharge, paid 5000, refund 1000 -> netPaid 4000, due 1700
try {
    $p = paidOrder(5000, 'rpos');
    $p['c']->adjustmentService->add($p['orderId'], 700, 'late fee');
    $p['c']->refundService->refund($p['paymentId'], 1000);
    $row = rowFor($p['c'], $p['orderId']);
    $results['refund_after_positive_adjustment'] =
        $row !== null
        && $row['adjustmentsCents'] === 700
        && $row['paidCents'] === 4000
        && $row['dueCents'] === 1700;
} catch (\Throwable $e) {
}

// --- refund_after_negative_adjustment ---
// gross 5000, -1200 discount, paid 5000, refund 800 -> netPaid 4200, due -400
try {
    $p = paidOrder(5000, 'rneg');
    $p['c']->adjustmentService->add($p['orderId'], -1200, 'goodwill discount');
    $p['c']->refundService->refund($p['paymentId'], 800);
    $row = rowFor($p['c'], $p['orderId']);
    $results['refund_after_negative_adjustment'] =
        $row !== null
        && $row['adjustmentsCents'] === -1200
        && $row['paidCents'] === 4200
        && $row['dueCents'] === -400;
} catch (\Throwable $e) {
}

// --- partial_refund: no adjustment, partial refund raises due exactly ---
// gross 5000, paid 5000, refund 1500 -> netPaid 3500, due 1500
try {
    $p = paidOrder(5000, 'rpart');
    $p['c']->refundService->refund($p['paymentId'], 1500);
    $row = rowFor($p['c'], $p['orderId']);
    $results['partial_refund'] =
        $row !== null
        && $row['adjustmentsCents'] === 0
        && $row['paidCents'] === 3500
        && $row['dueCents'] === 1500;
} catch (\Throwable $e) {
}

// --- full_refund: full refund returns due to the gross owed ---
// gross 5000, paid 5000, refund 5000 -> netPaid 0, due 5000
try {
    $p = paidOrder(5000, 'rfull');
    $p['c']->refundService->refund($p['paymentId'], 5000);
    $row = rowFor($p['c'], $p['orderId']);
    $results['full_refund'] =
        $row !== null
        && $row['paidCents'] === 0
        && $row['dueCents'] === 5000;
} catch (\Throwable $e) {
}

// --- adjustment_plus_refund_reconciliation ---
// gross + adjustments - paid === due holds with both components present.
try {
    $p = paidOrder(4000, 'recon');
    $p['c']->adjustmentService->add($p['orderId'], 500, 'surcharge');
    $p['c']->adjustmentService->add($p['orderId'], -300, 'discount');
    $p['c']->refundService->refund($p['paymentId'], 1000);
    $ok = true;
    $rows = $p['c']->invoiceService->summary();
    foreach ($rows as $row) {
        if ($row['grossCents'] + $row['adjustmentsCents'] - $row['paidCents'] !== $row['dueCents']) {
            $ok = false;
        }
    }
    $row = rowFor($p['c'], $p['orderId']);
    // 4000 + 200 - (4000 - 1000) = 1200
    $results['adjustment_plus_refund_reconciliation'] =
        $ok
        && $row !== null
        && $row['paidCents'] === 3000
        && $row['dueCents'] === 1200;
} catch (\Throwable $e) {
}

// --- stage1_public_fields_unchanged: exact field set, no additions ---
try {
    $p = paidOrder(5000, 'fields');
    $p['c']->adjustmentService->add($p['orderId'], 300, 'fee');
    $p['c']->refundService->refund($p['paymentId'], 500);
    $row = rowFor($p['c'], $p['orderId']);
    $expected = ['orderId', 'grossCents', 'adjustmentsCents', 'paidCents', 'dueCents'];
    $keys = $row === null ? [] : array_keys($row);
    sort($keys);
    $exp = $expected;
    sort($exp);
    $results['stage1_public_fields_unchanged'] = $keys === $exp;
} catch (\Throwable $e) {
}

echo json_encode($results);
exit(0);
