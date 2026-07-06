<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

/** A standard cart of one line item. */
function makeCart(string $id, int $qty, int $unit): Cart
{
    return new Cart($id, 'USD', [
        ['sku' => 'C', 'quantity' => $qty, 'unitCents' => $unit],
    ]);
}

$results = [];

// --- a same-cart retry reuses the existing pending order ---
$c = new Container();
$cart = makeCart('cart_s', 2, 500);
$o1 = $c->checkout->checkout('sess', $cart);
$o2 = $c->checkout->checkout('sess', $cart);
$results['same_cart_retry_reuses_order'] = $o1->id === $o2->id;

// --- a changed-cart retry creates a new order ---
$c2 = new Container();
$o1b = $c2->checkout->checkout('sess', makeCart('cart_c', 2, 500));
$o2b = $c2->checkout->checkout('sess', makeCart('cart_c', 3, 500));
$results['changed_cart_retry_new_order'] = $o1b->id !== $o2b->id;

// --- a failed attempt does not block a later successful payment ---
$c3 = new Container();
$cart3 = makeCart('cart_f', 1, 1000);
$o3 = $c3->checkout->checkout('sess', $cart3);
$failBody = json_encode([
    'id' => 'evt_cf_fail',
    'data' => ['object' => ['id' => 'pi_cf_fail', 'amount' => 1000, 'currency' => 'usd', 'status' => 'declined']],
], JSON_THROW_ON_ERROR);
$c3->webhookService->handle('stripe', $failBody, ['Stripe-Signature' => StripeMockGateway::sign($failBody)]);
$okBody = json_encode([
    'id' => 'evt_cf_ok',
    'data' => ['object' => ['id' => 'pi_cf_ok', 'amount' => 1000, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$res = $c3->webhookService->handle('stripe', $okBody, ['Stripe-Signature' => StripeMockGateway::sign($okBody)]);
$ord3 = $c3->orders->find($o3->id);
$results['failed_then_paid'] =
    $res['applied'] === true && $ord3 !== null && $ord3->status === PaymentStatus::PAID;

// --- two sessions with the same cart get distinct orders ---
$c4 = new Container();
$cart4 = makeCart('cart_two', 1, 700);
$oa = $c4->checkout->checkout('sess_a', $cart4);
$ob = $c4->checkout->checkout('sess_b', $cart4);
$results['two_sessions_distinct'] = $oa->id !== $ob->id;

// --- at most one invoice per order across same-cart retries ---
$c5 = new Container();
$cart5 = makeCart('cart_inv', 1, 1500);
$c5->checkout->checkout('sess', $cart5);
$c5->checkout->checkout('sess', $cart5);
$c5->checkout->checkout('sess', $cart5);
$results['invoice_count_stable'] = count($c5->invoices->all()) === 1;

// --- distinct payment attempts are tracked as distinct payments ---
$c6 = new Container();
$cart6 = makeCart('cart_att', 1, 1000);
$o6 = $c6->checkout->checkout('sess', $cart6);
$b1 = json_encode([
    'id' => 'evt_a1',
    'data' => ['object' => ['id' => 'pi_a1', 'amount' => 1000, 'currency' => 'usd', 'status' => 'declined']],
], JSON_THROW_ON_ERROR);
$c6->webhookService->handle('stripe', $b1, ['Stripe-Signature' => StripeMockGateway::sign($b1)]);
$b2 = json_encode([
    'id' => 'evt_a2',
    'data' => ['object' => ['id' => 'pi_a2', 'amount' => 1000, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$c6->webhookService->handle('stripe', $b2, ['Stripe-Signature' => StripeMockGateway::sign($b2)]);
$results['payment_attempts_distinct'] =
    count($c6->payments->findByOrder($o6->id)) === 2;

echo json_encode($results);
exit(0);
