<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Payment\StripeMockGateway;

/**
 * Fresh container with one order of $total cents, paid in full unless $pay=false.
 *
 * @return array{c: Container, orderId: string}
 */
function paidOrder(int $total, string $tag, bool $pay = true): array
{
    $c = new Container();
    $cart = new Cart('cart_' . $tag, 'USD', [
        ['sku' => $tag, 'quantity' => 1, 'unitCents' => $total],
    ]);
    $order = $c->checkout->checkout('sess_' . $tag, $cart);

    if ($pay) {
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
    }

    return ['c' => $c, 'orderId' => $order->id];
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
    'positive_adjustment' => false,
    'negative_adjustment' => false,
    'multiple_adjustments' => false,
    'adjustment_reason_preserved' => false,
    'summary_reconciles' => false,
    'old_invoices_without_adjustments_unchanged' => false,
];

// --- positive_adjustment: a surcharge raises adjustments and due ---
try {
    $p = paidOrder(5000, 'pos');
    $p['c']->adjustmentService->add($p['orderId'], 700, 'late fee');
    $row = rowFor($p['c'], $p['orderId']);
    $results['positive_adjustment'] =
        $row !== null
        && $row['grossCents'] === 5000
        && $row['adjustmentsCents'] === 700
        && $row['paidCents'] === 5000
        && $row['dueCents'] === 700;
} catch (\Throwable $e) {
}

// --- negative_adjustment: a discount lowers due ---
try {
    $p = paidOrder(5000, 'neg');
    $p['c']->adjustmentService->add($p['orderId'], -1200, 'goodwill discount');
    $row = rowFor($p['c'], $p['orderId']);
    $results['negative_adjustment'] =
        $row !== null
        && $row['adjustmentsCents'] === -1200
        && $row['dueCents'] === -1200;
} catch (\Throwable $e) {
}

// --- multiple_adjustments: net of several signed adjustments ---
try {
    $p = paidOrder(5000, 'multi');
    $p['c']->adjustmentService->add($p['orderId'], 700, 'surcharge');
    $p['c']->adjustmentService->add($p['orderId'], -200, 'discount');
    $p['c']->adjustmentService->add($p['orderId'], 150, 'admin fee');
    $row = rowFor($p['c'], $p['orderId']);
    $results['multiple_adjustments'] =
        $row !== null
        && $row['adjustmentsCents'] === 650
        && $row['dueCents'] === 650;
} catch (\Throwable $e) {
}

// --- adjustment_reason_preserved: reason + createdAt survive on the record ---
try {
    $p = paidOrder(5000, 'reason');
    $adj = $p['c']->adjustmentService->add($p['orderId'], 300, 'manual surcharge');
    $stored = $p['c']->adjustmentsRepo->findByOrder($p['orderId']);
    $results['adjustment_reason_preserved'] =
        count($stored) === 1
        && $stored[0]->reason === 'manual surcharge'
        && $stored[0]->amountCents === 300
        && is_string($stored[0]->createdAt)
        && $stored[0]->createdAt !== '';
} catch (\Throwable $e) {
}

// --- summary_reconciles: gross + adjustments - paid === due for every row ---
try {
    $p = paidOrder(4000, 'recon');
    $p['c']->adjustmentService->add($p['orderId'], 500, 'surcharge');
    $p['c']->adjustmentService->add($p['orderId'], -300, 'discount');
    $ok = true;
    $rows = $p['c']->invoiceService->summary();
    foreach ($rows as $row) {
        if ($row['grossCents'] + $row['adjustmentsCents'] - $row['paidCents'] !== $row['dueCents']) {
            $ok = false;
        }
    }
    $results['summary_reconciles'] = $ok && count($rows) >= 1;
} catch (\Throwable $e) {
}

// --- old_invoices_without_adjustments_unchanged ---
try {
    // Unpaid, no adjustments: due == gross, adjustments == 0.
    $p = paidOrder(2500, 'old_unpaid', false);
    $rowU = rowFor($p['c'], $p['orderId']);
    // Paid, no adjustments: due == 0, adjustments == 0.
    $p2 = paidOrder(2500, 'old_paid');
    $rowP = rowFor($p2['c'], $p2['orderId']);
    $results['old_invoices_without_adjustments_unchanged'] =
        $rowU !== null
        && $rowU['adjustmentsCents'] === 0
        && $rowU['paidCents'] === 0
        && $rowU['dueCents'] === 2500
        && $rowP !== null
        && $rowP['adjustmentsCents'] === 0
        && $rowP['paidCents'] === 2500
        && $rowP['dueCents'] === 0;
} catch (\Throwable $e) {
}

echo json_encode($results);
exit(0);
