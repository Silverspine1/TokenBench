<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\PaymentStatus;
use App\Payment\StripeMockGateway;

/**
 * Fresh container with one fully-paid order of $amount cents.
 *
 * @return array{c: Container, orderId: string, paymentId: string}
 */
function paidOrder(int $amount): array
{
    $c = new Container();
    $cart = new Cart('cart_ref', 'USD', [
        ['sku' => 'R', 'quantity' => 1, 'unitCents' => $amount],
    ]);
    $order = $c->checkout->checkout('sess', $cart);

    $body = json_encode([
        'id' => 'evt_paid',
        'data' => ['object' => [
            'id' => 'pi_paid',
            'amount' => $amount,
            'currency' => 'usd',
            'status' => 'succeeded',
        ]],
    ], JSON_THROW_ON_ERROR);
    $headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
    $c->webhookService->handle('stripe', $body, $headers);

    $payment = $c->payments->findByReference('pi_paid');

    return ['c' => $c, 'orderId' => $order->id, 'paymentId' => $payment->id];
}

/**
 * Fresh container with one order carrying TWO distinct successful payments.
 *
 * @return array{c: Container, orderId: string, paymentA: string, paymentB: string}
 */
function twoPaymentOrder(int $amount): array
{
    $c = new Container();
    $cart = new Cart('cart_two', 'USD', [
        ['sku' => 'T', 'quantity' => 1, 'unitCents' => $amount],
    ]);
    $order = $c->checkout->checkout('sess', $cart);

    foreach ([['evt_two_a', 'pi_two_a'], ['evt_two_b', 'pi_two_b']] as [$eid, $ref]) {
        $body = json_encode([
            'id' => $eid,
            'data' => ['object' => [
                'id' => $ref,
                'amount' => $amount,
                'currency' => 'usd',
                'status' => 'succeeded',
            ]],
        ], JSON_THROW_ON_ERROR);
        $headers = ['Stripe-Signature' => StripeMockGateway::sign($body)];
        $c->webhookService->handle('stripe', $body, $headers);
    }

    $a = $c->payments->findByReference('pi_two_a');
    $b = $c->payments->findByReference('pi_two_b');

    return ['c' => $c, 'orderId' => $order->id, 'paymentA' => $a->id, 'paymentB' => $b->id];
}

$results = [];

// --- partial refund updates invoice balance exactly ---
$p = paidOrder(5000);
$p['c']->refundService->refund($p['paymentId'], 1500);
$inv = $p['c']->invoices->findByOrder($p['orderId']);
$results['partial_refund_updates_balance'] =
    $inv !== null && $inv->refundedCents === 1500 && $inv->netPaidCents() === 3500;

// --- full refund updates invoice balance exactly ---
$p2 = paidOrder(5000);
$p2['c']->refundService->refund($p2['paymentId'], 5000);
$inv2 = $p2['c']->invoices->findByOrder($p2['orderId']);
$results['full_refund_updates_balance'] =
    $inv2 !== null && $inv2->refundedCents === 5000 && $inv2->netPaidCents() === 0;

// --- refund record is visible in the payment log ---
$p3 = paidOrder(5000);
$refund = $p3['c']->refundService->refund($p3['paymentId'], 2000);
$logged = $p3['c']->refunds->findByPayment($p3['paymentId']);
$results['refund_visible_in_log'] =
    count($logged) === 1 && $logged[0]->amountCents === 2000;

// --- a refund cannot exceed the amount paid ---
$p4 = paidOrder(5000);
$rejected = false;
try {
    $p4['c']->refundService->refund($p4['paymentId'], 9000);
} catch (\DomainException $e) {
    $rejected = true;
}
$results['over_refund_rejected'] = $rejected;

// --- order status reflects the refunded state ---
$p5 = paidOrder(5000);
$p5['c']->refundService->refund($p5['paymentId'], 2000);
$ord5 = $p5['c']->orders->find($p5['orderId']);
$partialOk = $ord5 !== null && $ord5->status === PaymentStatus::PARTIALLY_REFUNDED;
$p5['c']->refundService->refund($p5['paymentId'], 3000);
$ord5b = $p5['c']->orders->find($p5['orderId']);
$fullOk = $ord5b !== null && $ord5b->status === PaymentStatus::REFUNDED;
$results['order_status_reconciles'] = $partialOk && $fullOk;

// --- invoice balance is exact after a sequence of refunds ---
$p6 = paidOrder(5000);
$p6['c']->refundService->refund($p6['paymentId'], 1000);
$p6['c']->refundService->refund($p6['paymentId'], 1500);
$inv6 = $p6['c']->invoices->findByOrder($p6['orderId']);
$results['invoice_balance_exact'] =
    $inv6 !== null && $inv6->refundedCents === 2500 && $inv6->netPaidCents() === 2500;

// --- refunds across every payment of an order are counted exactly ---
$p7 = twoPaymentOrder(5000);
$p7['c']->refundService->refund($p7['paymentA'], 1000);
$p7['c']->refundService->refund($p7['paymentB'], 1500);
$inv7 = $p7['c']->invoices->findByOrder($p7['orderId']);
$results['refund_across_multiple_payments_exact'] =
    $inv7 !== null
    && $inv7->paidCents === 10000
    && $inv7->refundedCents === 2500
    && $inv7->netPaidCents() === 7500;

echo json_encode($results);
exit(0);
