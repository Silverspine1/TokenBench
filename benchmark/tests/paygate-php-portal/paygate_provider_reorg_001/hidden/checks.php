<?php

declare(strict_types=1);

// Hidden behaviour checks for the provider reorganization. Each behavioural
// check is gated on the relevant provider module existing at its CANONICAL
// PSR-4 path (app/Payment/*). The flattened "broken" layout keeps the same
// behaviour reachable through legacy catch-all files, so behaviour alone is not
// enough: a check passes only when the behaviour works AND the code lives at the
// canonical module path. Each check is independent (graceful partial credit).

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\PayFastMockGateway;
use App\Payment\StripeMockGateway;

function canon(string $ws, string $rel): bool
{
    return is_file($ws . '/' . $rel);
}

$INTERFACE = 'app/Payment/GatewayInterface.php';
$STRIPE = 'app/Payment/StripeMockGateway.php';
$PAYFAST = 'app/Payment/PayFastMockGateway.php';
$VERIFIER = 'app/Payment/WebhookVerifier.php';
$NORMALIZER = 'app/Payment/GatewayEventNormalizer.php';

$allCanon = canon($ws, $INTERFACE)
    && canon($ws, $STRIPE)
    && canon($ws, $PAYFAST)
    && canon($ws, $VERIFIER)
    && canon($ws, $NORMALIZER);

/** Fresh order paid via a Stripe-like webhook for $amount cents in USD. */
function stripePaidOrder(int $amount): array
{
    $c = new Container();
    $cart = new Cart('cart_s', 'USD', [['sku' => 'S', 'quantity' => 1, 'unitCents' => $amount]]);
    $order = $c->checkout->checkout('sess', $cart);
    $body = json_encode([
        'id' => 'evt_s',
        'data' => ['object' => ['id' => 'pi_s', 'amount' => $amount, 'currency' => 'usd', 'status' => 'succeeded']],
    ], JSON_THROW_ON_ERROR);
    $headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
    $applied = $c->webhookService->handle('stripe', $body, $headers);

    return ['c' => $c, 'orderId' => $order->id, 'applied' => $applied];
}

$results = [];

// --- checkout still works (order + invoice created, due = total) ---
try {
    $c = new Container();
    $cart = new Cart('cart_co', 'USD', [['sku' => 'A', 'quantity' => 2, 'unitCents' => 1500]]);
    $order = $c->checkout->checkout('sess', $cart);
    $inv = $c->invoices->findByOrder($order->id);
    $results['checkout_still_works'] = $allCanon
        && $order->totalCents === 3000
        && $inv !== null
        && $inv->paidCents === 0;
} catch (\Throwable $e) {
    $results['checkout_still_works'] = false;
}

// --- Stripe-like webhook still works (invoice marked paid, order PAID) ---
try {
    $p = stripePaidOrder(5000);
    $inv = $p['c']->invoices->findByOrder($p['orderId']);
    $ord = $p['c']->orders->find($p['orderId']);
    $results['stripe_webhook_still_works'] =
        canon($ws, $STRIPE) && canon($ws, $VERIFIER) && canon($ws, $NORMALIZER) && canon($ws, $INTERFACE)
        && $inv !== null && $inv->paidCents === 5000
        && $ord !== null && $ord->status === PaymentStatus::PAID;
} catch (\Throwable $e) {
    $results['stripe_webhook_still_works'] = false;
}

// --- PayFast-like webhook still works ---
try {
    $c = new Container();
    $cart = new Cart('cart_pf', 'USD', [['sku' => 'P', 'quantity' => 1, 'unitCents' => 5000]]);
    $order = $c->checkout->checkout('sess', $cart);
    $body = json_encode([
        'payment_id' => 'evt_pf',
        'reference' => 'pf_ref',
        'amount' => '50.00',
        'currency' => 'USD',
        'status' => 'complete',
    ], JSON_THROW_ON_ERROR);
    $headers = ['X-PayFast-Signature' => PayFastMockGateway::sign($body)];
    $c->webhookService->handle('payfast', $body, $headers);
    $inv = $c->invoices->findByOrder($order->id);
    $ord = $c->orders->find($order->id);
    $results['payfast_webhook_still_works'] =
        canon($ws, $PAYFAST) && canon($ws, $VERIFIER) && canon($ws, $NORMALIZER) && canon($ws, $INTERFACE)
        && $inv !== null && $inv->paidCents === 5000
        && $ord !== null && $ord->status === PaymentStatus::PAID;
} catch (\Throwable $e) {
    $results['payfast_webhook_still_works'] = false;
}

// --- admin payment report unchanged for a paid order ---
try {
    $p = stripePaidOrder(7000);
    $rows = $p['c']->reportService->report();
    $row = null;
    foreach ($rows as $r) {
        if ($r['orderId'] === $p['orderId']) {
            $row = $r;
            break;
        }
    }
    $results['admin_report_unchanged'] = $allCanon
        && $row !== null
        && $row['totalCents'] === 7000
        && $row['paidCents'] === 7000
        && $row['dueCents'] === 0
        && $row['status'] === PaymentStatus::PAID;
} catch (\Throwable $e) {
    $results['admin_report_unchanged'] = false;
}

// --- legacy public entrypoint still works (container wiring intact) ---
try {
    $entrypointOk = is_file($ws . '/public/index.php');
    $c = new Container();
    $wired = $c->checkoutController !== null
        && $c->webhookController !== null
        && $c->refundController !== null
        && $c->adminController !== null;
    $results['legacy_entrypoint_still_works'] = $allCanon && $entrypointOk && $wired;
} catch (\Throwable $e) {
    $results['legacy_entrypoint_still_works'] = false;
}

echo json_encode($results);
exit(0);
