<?php

declare(strict_types=1);

// Reorg smoke test. Exercises the public payment flow through the wired
// Container only, so it runs regardless of how the provider code is laid out
// internally (legacy catch-all files or canonical App\Payment modules).
//   php tests_visible/run_reorg_smoke.php

require __DIR__ . '/../app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

$failures = 0;
$check = static function (string $name, bool $cond) use (&$failures): void {
    echo ($cond ? 'ok - ' : 'not ok - ') . $name . "\n";
    if (!$cond) {
        $failures++;
    }
};

$c = new Container();
$cart = new Cart('cart_smoke', 'USD', [['sku' => 'X', 'quantity' => 1, 'unitCents' => 5000]]);
$order = $c->checkout->checkout('sess', $cart);
$check('checkout creates order', $order->totalCents === 5000);

$body = json_encode([
    'id' => 'evt_smoke',
    'data' => ['object' => ['id' => 'pi_smoke', 'amount' => 5000, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
$c->webhookService->handle('stripe', $body, $headers);

$inv = $c->invoices->findByOrder($order->id);
$check('stripe webhook marks invoice paid', $inv !== null && $inv->paidCents === 5000);

$ord = $c->orders->find($order->id);
$check('order reconciles to PAID', $ord !== null && $ord->status === PaymentStatus::PAID);

$rows = $c->reportService->report();
$check('admin report lists the order', count($rows) >= 1);

echo $failures === 0 ? "reorg smoke OK\n" : "reorg smoke FAILED ($failures)\n";
exit($failures === 0 ? 0 : 1);
