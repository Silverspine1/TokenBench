<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

/**
 * Drive a single fully-paid order of $totalCents through checkout + a stripe
 * webhook, then recompute the invoice via InvoiceService. Returns the container
 * plus the order so callers can inspect derived figures.
 *
 * @return array{c: Container, orderId: string}
 */
function payOrder(int $totalCents): array
{
    $c = new Container();
    $cart = new Cart('cart_' . $totalCents, 'USD', [
        ['sku' => 'X', 'quantity' => 1, 'unitCents' => $totalCents],
    ]);
    $order = $c->checkout->checkout('sess', $cart);

    $body = json_encode([
        'id' => 'evt_' . $totalCents,
        'data' => ['object' => [
            'id' => 'pi_' . $totalCents,
            'amount' => $totalCents,
            'currency' => 'usd',
            'status' => 'succeeded',
        ]],
    ], JSON_THROW_ON_ERROR);
    $headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
    $c->webhookService->handle('stripe', $body, $headers);

    $c->invoiceService->recompute($order->id);

    return ['c' => $c, 'orderId' => $order->id];
}

/**
 * Drive a part-paid order: total $totalCents with a single paid payment of
 * $paidCents (located by amount, so the order total must equal $paidCents for
 * the webhook to match; instead we drive payment directly through a matching
 * pending order whose total equals the payment amount, then assert reporting).
 *
 * @return array{c: Container, orderId: string}
 */
function partPaidOrder(int $totalCents, int $paidCents): array
{
    $c = new Container();
    // Order total is the full amount; a partial payment of $paidCents arrives.
    $cart = new Cart('cart_pp', 'USD', [
        ['sku' => 'Y', 'quantity' => 1, 'unitCents' => $totalCents],
    ]);
    $order = $c->checkout->checkout('sess', $cart);

    // Build a pending sibling order matching the partial amount so the webhook
    // locator can attach the payment, then move the payment onto the real order.
    $payment = new \App\Domain\Payment(
        $c->db->nextId('payment'),
        $order->id,
        'pi_pp',
        'evt_pp',
        $paidCents,
        'USD',
        PaymentStatus::PAID
    );
    $c->payments->save($payment);
    $c->invoiceService->recompute($order->id);

    return ['c' => $c, 'orderId' => $order->id];
}

$results = [];

// --- round-number amount reconciles exactly ---
$r = payOrder(2000);
$inv = $r['c']->invoices->findByOrder($r['orderId']);
$results['reconcile_round_amounts'] =
    $inv !== null && $inv->paidCents === 2000 && $inv->dueCents() === 0;

// --- odd-cent amount reconciles exactly ---
$r = payOrder(113);
$inv = $r['c']->invoices->findByOrder($r['orderId']);
$results['reconcile_odd_cents'] =
    $inv !== null && $inv->paidCents === 113 && $inv->dueCents() === 0;

// --- part-paid order remains outstanding ---
$r = partPaidOrder(1999, 1000);
$inv = $r['c']->invoices->findByOrder($r['orderId']);
$results['part_paid_remains_outstanding'] =
    $inv !== null && $inv->paidCents === 1000 && $inv->dueCents() === 999;

// --- fully-paid invoice shows zero due ---
$r = payOrder(1999);
$inv = $r['c']->invoices->findByOrder($r['orderId']);
$results['paid_invoice_due_zero'] =
    $inv !== null && $inv->dueCents() === 0;

// --- admin report: paid + due == total for a part-paid odd-cent order ---
$r = partPaidOrder(1999, 1000);
$report = $r['c']->reportService->report();
$ok = false;
foreach ($report as $row) {
    if ($row['orderId'] === $r['orderId']) {
        $ok = ($row['paidCents'] + $row['dueCents']) === $row['totalCents']
            && $row['totalCents'] === 1999
            && $row['paidCents'] === 1000;
    }
}
$results['admin_paid_plus_due_equals_total'] = $ok;

// --- currency is preserved through reporting ---
$r = payOrder(2500);
$report = $r['c']->reportService->report();
$ok = false;
foreach ($report as $row) {
    if ($row['orderId'] === $r['orderId']) {
        $ok = $row['currency'] === 'USD';
    }
}
$results['currency_unchanged'] = $ok;

echo json_encode($results);
exit(0);
