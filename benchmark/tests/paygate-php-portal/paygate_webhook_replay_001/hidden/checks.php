<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

/**
 * Build a signed stripe webhook body for the given event/payment identifiers.
 */
function stripeEvent(string $eventId, string $ref, int $amount, string $status): array
{
    $body = json_encode([
        'id' => $eventId,
        'data' => ['object' => [
            'id' => $ref,
            'amount' => $amount,
            'currency' => 'usd',
            'status' => $status,
        ]],
    ], JSON_THROW_ON_ERROR);

    return [$body, ['Stripe-Signature' => StripeMockGateway::sign($body)]];
}

/** Build a fresh container with one pending order of $amount cents. */
function freshOrder(int $amount): array
{
    $c = new Container();
    $cart = new Cart('cart_w', 'USD', [
        ['sku' => 'W', 'quantity' => 1, 'unitCents' => $amount],
    ]);
    $order = $c->checkout->checkout('sess', $cart);

    return ['c' => $c, 'orderId' => $order->id];
}

$results = [];

// --- replaying the same event does not duplicate the payment ---
$f = freshOrder(2234);
[$body, $headers] = stripeEvent('evt_r1', 'pi_r1', 2234, 'succeeded');
$f['c']->webhookService->handle('stripe', $body, $headers);
$f['c']->webhookService->handle('stripe', $body, $headers);
$f['c']->webhookService->handle('stripe', $body, $headers);
$results['same_event_replay_payment_count'] =
    count($f['c']->payments->findByOrder($f['orderId'])) === 1;

// --- replaying the same event does not inflate the invoice total ---
$inv = $f['c']->invoices->findByOrder($f['orderId']);
$results['same_event_replay_invoice_total'] =
    $inv !== null && $inv->paidCents === 2234;

// --- a distinct event with the same already-paid reference does not double-pay ---
$f2 = freshOrder(2234);
[$b1, $h1] = stripeEvent('evt_d1', 'pi_dup', 2234, 'succeeded');
$f2['c']->webhookService->handle('stripe', $b1, $h1);
[$b2, $h2] = stripeEvent('evt_d2', 'pi_dup', 2234, 'succeeded');
$f2['c']->webhookService->handle('stripe', $b2, $h2);
$inv2 = $f2['c']->invoices->findByOrder($f2['orderId']);
$results['distinct_event_same_reference_no_double_pay'] =
    $inv2 !== null && $inv2->paidCents === 2234;

// --- out-of-order delivery is handled without error ---
$f3 = freshOrder(1500);
[$bf, $hf] = stripeEvent('evt_o_fail', 'pi_o', 1500, 'declined');
[$bp, $hp] = stripeEvent('evt_o_paid', 'pi_o2', 1500, 'succeeded');
$f3['c']->webhookService->handle('stripe', $bp, $hp);
$f3['c']->webhookService->handle('stripe', $bf, $hf);
$ord3 = $f3['c']->orders->find($f3['orderId']);
$results['out_of_order_handled'] =
    $ord3 !== null && $ord3->status === PaymentStatus::PAID;

// --- a failed attempt does not block a later success ---
$f4 = freshOrder(1000);
[$bf2, $hf2] = stripeEvent('evt_f_fail', 'pi_f', 1000, 'declined');
$f4['c']->webhookService->handle('stripe', $bf2, $hf2);
[$bp2, $hp2] = stripeEvent('evt_f_ok', 'pi_f2', 1000, 'succeeded');
$res4 = $f4['c']->webhookService->handle('stripe', $bp2, $hp2);
$ord4 = $f4['c']->orders->find($f4['orderId']);
$results['failed_then_success'] =
    $res4['applied'] === true
    && $ord4 !== null && $ord4->status === PaymentStatus::PAID;

// --- a later failed notification does not pull a paid order back to failed ---
$f6 = freshOrder(1750);
[$bp6, $hp6] = stripeEvent('evt_p_ok', 'pi_p6', 1750, 'succeeded');
$f6['c']->webhookService->handle('stripe', $bp6, $hp6);
$ord6paid = $f6['c']->orders->find($f6['orderId']);
$inv6paid = $f6['c']->invoices->findByOrder($f6['orderId']);
$paidThenOk = $ord6paid !== null && $ord6paid->status === PaymentStatus::PAID
    && $inv6paid !== null && $inv6paid->paidCents === 1750;
[$bf6, $hf6] = stripeEvent('evt_p_fail', 'pi_p6b', 1750, 'declined');
$f6['c']->webhookService->handle('stripe', $bf6, $hf6);
$ord6 = $f6['c']->orders->find($f6['orderId']);
$inv6 = $f6['c']->invoices->findByOrder($f6['orderId']);
$results['failed_after_paid_keeps_paid'] =
    $paidThenOk
    && $ord6 !== null && $ord6->status === PaymentStatus::PAID
    && $inv6 !== null && $inv6->paidCents === 1750;

// --- invalid signatures are rejected before any state change ---
$f5 = freshOrder(800);
[$bb, ] = stripeEvent('evt_bad', 'pi_bad', 800, 'succeeded');
$res5 = $f5['c']->webhookService->handle('stripe', $bb, ['Stripe-Signature' => 'deadbeef']);
$results['invalid_signature_rejected'] =
    $res5['applied'] === false
    && $res5['reason'] === 'invalid_signature'
    && $f5['c']->payments->findByReference('pi_bad') === null;

echo json_encode($results);
exit(0);
