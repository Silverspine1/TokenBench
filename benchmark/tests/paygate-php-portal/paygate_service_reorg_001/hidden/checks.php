<?php

declare(strict_types=1);

// Hidden behaviour checks for the payment-flow reorganization. Each behavioural
// check is gated on the relevant service/controller existing at its CANONICAL
// PSR-4 path (app/Services/* and app/Controllers/*). The flattened "broken"
// layout keeps the same behaviour reachable through legacy catch-all files, so
// behaviour alone is not enough: a check passes only when the behaviour works
// AND the code lives at the canonical path. Each check is independent (graceful
// partial credit).

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

function canon(string $ws, string $rel): bool
{
    return is_file($ws . '/' . $rel);
}

$CHECKOUT_SVC = 'app/Services/CheckoutService.php';
$WEBHOOK_SVC = 'app/Services/WebhookService.php';
$REFUND_SVC = 'app/Services/RefundService.php';
$CHECKOUT_CTRL = 'app/Controllers/CheckoutController.php';
$WEBHOOK_CTRL = 'app/Controllers/WebhookController.php';
$REFUND_CTRL = 'app/Controllers/RefundController.php';

$allCanon = canon($ws, $CHECKOUT_SVC)
    && canon($ws, $WEBHOOK_SVC)
    && canon($ws, $REFUND_SVC)
    && canon($ws, $CHECKOUT_CTRL)
    && canon($ws, $WEBHOOK_CTRL)
    && canon($ws, $REFUND_CTRL);

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

// --- checkout orchestration creates an order + invoice (due = total) ---
try {
    $c = new Container();
    $cart = new Cart('cart_co', 'USD', [['sku' => 'A', 'quantity' => 2, 'unitCents' => 1500]]);
    $order = $c->checkout->checkout('sess', $cart);
    $inv = $c->invoices->findByOrder($order->id);
    $results['checkout_request_creates_attempt'] =
        canon($ws, $CHECKOUT_SVC) && canon($ws, $CHECKOUT_CTRL)
        && $order->totalCents === 3000
        && $inv !== null
        && $inv->paidCents === 0;
} catch (\Throwable $e) {
    $results['checkout_request_creates_attempt'] = false;
}

// --- webhook handling marks the invoice paid and the order PAID ---
try {
    $p = stripePaidOrder(5000);
    $inv = $p['c']->invoices->findByOrder($p['orderId']);
    $ord = $p['c']->orders->find($p['orderId']);
    $results['webhook_updates_invoice'] =
        canon($ws, $WEBHOOK_SVC) && canon($ws, $WEBHOOK_CTRL)
        && $inv !== null && $inv->paidCents === 5000
        && $ord !== null && $ord->status === PaymentStatus::PAID;
} catch (\Throwable $e) {
    $results['webhook_updates_invoice'] = false;
}

// --- refund handling updates the invoice (refundedCents) and order status ---
try {
    $p = stripePaidOrder(6000);
    $c = $p['c'];
    $payment = null;
    foreach ($c->payments->findByOrder($p['orderId']) as $pay) {
        $payment = $pay;
        break;
    }
    $c->refundService->refund($payment->id, 2000);
    $inv = $c->invoices->findByOrder($p['orderId']);
    $ord = $c->orders->find($p['orderId']);
    $results['refund_updates_payment_and_invoice'] =
        canon($ws, $REFUND_SVC) && canon($ws, $REFUND_CTRL)
        && $payment !== null
        && $inv !== null && $inv->refundedCents === 2000
        && $ord !== null && $ord->status === PaymentStatus::PARTIALLY_REFUNDED;
} catch (\Throwable $e) {
    $results['refund_updates_payment_and_invoice'] = false;
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

// --- controllers are thin request/response boundaries wired in the Container ---
try {
    $c = new Container();
    $wired = $c->checkoutController !== null
        && $c->webhookController !== null
        && $c->refundController !== null
        && $c->adminController !== null;
    $results['controllers_thin_boundary'] = $allCanon && $wired;
} catch (\Throwable $e) {
    $results['controllers_thin_boundary'] = false;
}

echo json_encode($results);
exit(0);
