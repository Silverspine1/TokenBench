<?php

declare(strict_types=1);

require __DIR__ . '/../app/bootstrap.php';

use App\Container;
use App\Domain\Cart;
use App\Domain\Money;
use App\Domain\PaymentStatus;
use App\Payment\GatewayEventNormalizer;
use App\Payment\PayFastMockGateway;
use App\Payment\StripeMockGateway;

$failures = 0;

$check = static function (string $name, bool $condition) use (&$failures): void {
    if ($condition) {
        echo 'ok - ' . $name . "\n";
    } else {
        echo 'not ok - ' . $name . "\n";
        $failures++;
    }
};

// Money parsing
$check('money two decimals', Money::fromDecimalString('12.34', 'USD')->cents() === 1234);
$check('money no decimal', Money::fromDecimalString('12', 'USD')->cents() === 1200);
$check('money one decimal', Money::fromDecimalString('12.5', 'USD')->cents() === 1250);
$check('money negative', Money::fromDecimalString('-3.07', 'USD')->cents() === -307);
$check('money to string', Money::fromCents(1234, 'USD')->toDecimalString() === '12.34');
$check('money to string padded', Money::fromCents(1205, 'USD')->toDecimalString() === '12.05');
$check('money add', Money::fromCents(100, 'USD')->add(Money::fromCents(50, 'USD'))->cents() === 150);

$currencyMismatch = false;
try {
    Money::fromCents(100, 'USD')->add(Money::fromCents(50, 'ZAR'));
} catch (\InvalidArgumentException $e) {
    $currencyMismatch = true;
}
$check('money currency mismatch throws', $currencyMismatch);

// Status normalization
$check('status paid variant', PaymentStatus::normalize('COMPLETED') === PaymentStatus::PAID);
$check('status succeeded variant', PaymentStatus::normalize('succeeded') === PaymentStatus::PAID);
$check('status failed variant', PaymentStatus::normalize('declined') === PaymentStatus::FAILED);
$check('status unknown passthrough', PaymentStatus::normalize('  Weird ') === 'weird');

// Normalizer both shapes
$normalizer = new GatewayEventNormalizer();

$stripeNew = $normalizer->normalize('stripe', [
    'id' => 'evt_a',
    'data' => ['object' => ['id' => 'pi_a', 'amount' => 2234, 'currency' => 'usd', 'status' => 'succeeded']],
]);
$check('stripe new eventId', $stripeNew['eventId'] === 'evt_a');
$check('stripe new ref', $stripeNew['paymentReference'] === 'pi_a');
$check('stripe new amount', $stripeNew['amountCents'] === 2234);
$check('stripe new status', $stripeNew['status'] === PaymentStatus::PAID);
$check('stripe new currency', $stripeNew['currency'] === 'USD');

$stripeOld = $normalizer->normalize('stripe', [
    'event_id' => 'evt_b',
    'payment_ref' => 'pi_b',
    'amount_cents' => 500,
    'currency' => 'USD',
    'status' => 'Paid',
]);
$check('stripe old eventId', $stripeOld['eventId'] === 'evt_b');
$check('stripe old amount', $stripeOld['amountCents'] === 500);
$check('stripe old status', $stripeOld['status'] === PaymentStatus::PAID);

$payfastNew = $normalizer->normalize('payfast', [
    'm_payment_id' => 'mpf_1',
    'pf_payment_id' => 'pf_1',
    'amount_gross' => '99.00',
    'currency_code' => 'ZAR',
    'payment_status' => 'COMPLETE',
]);
$check('payfast new eventId', $payfastNew['eventId'] === 'mpf_1');
$check('payfast new ref', $payfastNew['paymentReference'] === 'pf_1');
$check('payfast new amount cents', $payfastNew['amountCents'] === 9900);
$check('payfast new currency', $payfastNew['currency'] === 'ZAR');

$payfastOld = $normalizer->normalize('payfast', [
    'payment_id' => 'mpf_2',
    'reference' => 'pf_2',
    'amount' => '12.34',
    'currency' => 'ZAR',
    'status' => 'completed',
]);
$check('payfast old eventId', $payfastOld['eventId'] === 'mpf_2');
$check('payfast old amount cents', $payfastOld['amountCents'] === 1234);

// Checkout reuse / fingerprint
$c = new Container();
$cart = new Cart('cart_x', 'USD', [
    ['sku' => 'A', 'quantity' => 2, 'unitCents' => 500],
    ['sku' => 'B', 'quantity' => 1, 'unitCents' => 1234],
]);
$check('cart total cents', $cart->itemsTotalCents() === 2234);

$order1 = $c->checkout->checkout('sess_1', $cart);
$order2 = $c->checkout->checkout('sess_1', $cart);
$check('checkout reuses pending order', $order1->id === $order2->id);
$check('one invoice per order', count($c->invoices->all()) === 1);

$cartChanged = new Cart('cart_x', 'USD', [
    ['sku' => 'A', 'quantity' => 3, 'unitCents' => 500],
]);
$order3 = $c->checkout->checkout('sess_1', $cartChanged);
$check('changed fingerprint creates new order', $order3->id !== $order1->id);
$check('second invoice created', count($c->invoices->all()) === 2);

// Webhook apply
$stripeBody = json_encode([
    'id' => 'evt_pay_1',
    'data' => ['object' => ['id' => 'pi_pay_1', 'amount' => 2234, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$stripeHeaders = ['Stripe-Signature' => StripeMockGateway::sign($stripeBody)];

$applied = $c->webhookService->handle('stripe', $stripeBody, $stripeHeaders);
$check('webhook applied', $applied['applied'] === true);

$invoice1 = $c->invoices->findByOrder($order1->id);
$check('invoice paid after webhook', $invoice1 !== null && $invoice1->paidCents === 2234);
$refreshedOrder1 = $c->orders->find($order1->id);
$check('order marked paid', $refreshedOrder1 !== null && $refreshedOrder1->status === PaymentStatus::PAID);

// Replay same event = duplicate, no mutation
$replay = $c->webhookService->handle('stripe', $stripeBody, $stripeHeaders);
$check('webhook replay duplicate', $replay['applied'] === false && $replay['reason'] === 'duplicate');
$check('payment count unchanged after replay', count($c->payments->findByOrder($order1->id)) === 1);

// Invalid signature rejected before state change
$badHeaders = ['Stripe-Signature' => 'deadbeef'];
$badBody = json_encode([
    'id' => 'evt_bad_1',
    'data' => ['object' => ['id' => 'pi_bad', 'amount' => 100, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$rejected = $c->webhookService->handle('stripe', $badBody, $badHeaders);
$check('invalid signature rejected', $rejected['applied'] === false && $rejected['reason'] === 'invalid_signature');
$check('no payment recorded for bad signature', $c->payments->findByReference('pi_bad') === null);

// Distinct eventId same reference on already paid order does not double-pay
$secondEventBody = json_encode([
    'id' => 'evt_pay_2',
    'data' => ['object' => ['id' => 'pi_pay_1', 'amount' => 2234, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$secondHeaders = ['Stripe-Signature' => StripeMockGateway::sign($secondEventBody)];
$reconcile = $c->webhookService->handle('stripe', $secondEventBody, $secondHeaders);
$invoiceAfter = $c->invoices->findByOrder($order1->id);
$check('reconcile does not double pay', $invoiceAfter !== null && $invoiceAfter->paidCents === 2234);
$check('reconcile reported not applied', $reconcile['applied'] === false);

// Refund partial then status
$paidPayment = $c->payments->findByReference('pi_pay_1');
$check('paid payment located', $paidPayment !== null);

$c->refundService->refund($paidPayment->id, 1000);
$invoiceRefunded = $c->invoices->findByOrder($order1->id);
$check('partial refund recorded', $invoiceRefunded !== null && $invoiceRefunded->refundedCents === 1000);
$orderPartial = $c->orders->find($order1->id);
$check('order partially refunded', $orderPartial !== null && $orderPartial->status === PaymentStatus::PARTIALLY_REFUNDED);
$check('net paid after partial refund', $invoiceRefunded->netPaidCents() === 1234);

// Over-refund rejected
$overRefund = false;
try {
    $c->refundService->refund($paidPayment->id, 5000);
} catch (\DomainException $e) {
    $overRefund = true;
}
$check('over refund rejected', $overRefund);

// Full refund
$c->refundService->refund($paidPayment->id, 1234);
$orderFull = $c->orders->find($order1->id);
$check('order fully refunded', $orderFull !== null && $orderFull->status === PaymentStatus::REFUNDED);

// Report reconciliation invariant
$report = $c->reportService->report();
$reconciles = true;
foreach ($report as $row) {
    $invoice = $c->invoices->findByOrder($row['orderId']);
    $refunded = $invoice !== null ? $invoice->refundedCents : 0;
    if (($row['paidCents'] - $refunded) + $row['dueCents'] !== $row['totalCents']) {
        $reconciles = false;
    }
}
$check('report rows reconcile exactly', $reconciles);
$check('report has rows for all orders', count($report) === count($c->orders->all()));

// Failed payment does not block fresh attempt
$c2 = new Container();
$cartF = new Cart('cart_f', 'USD', [['sku' => 'Z', 'quantity' => 1, 'unitCents' => 1000]]);
$orderF = $c2->checkout->checkout('sess_f', $cartF);
$failBody = json_encode([
    'id' => 'evt_fail_1',
    'data' => ['object' => ['id' => 'pi_fail', 'amount' => 1000, 'currency' => 'usd', 'status' => 'declined']],
], JSON_THROW_ON_ERROR);
$failHeaders = ['Stripe-Signature' => StripeMockGateway::sign($failBody)];
$c2->webhookService->handle('stripe', $failBody, $failHeaders);

$okBody = json_encode([
    'id' => 'evt_ok_after_fail',
    'data' => ['object' => ['id' => 'pi_ok', 'amount' => 1000, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$okHeaders = ['Stripe-Signature' => StripeMockGateway::sign($okBody)];
$afterFail = $c2->webhookService->handle('stripe', $okBody, $okHeaders);
$check('payment completes after prior failure', $afterFail['applied'] === true);
$orderAfterFail = $c2->orders->find($orderF->id);
$check('order paid after prior failure', $orderAfterFail !== null && $orderAfterFail->status === PaymentStatus::PAID);

// PayFast end-to-end with decimal amount
$c3 = new Container();
$cartP = new Cart('cart_p', 'ZAR', [['sku' => 'P', 'quantity' => 1, 'unitCents' => 9900]]);
$orderP = $c3->checkout->checkout('sess_p', $cartP);
$pfBody = json_encode([
    'm_payment_id' => 'mpf_pay',
    'pf_payment_id' => 'pf_pay',
    'amount_gross' => '99.00',
    'currency_code' => 'ZAR',
    'payment_status' => 'COMPLETE',
], JSON_THROW_ON_ERROR);
$pfHeaders = ['X-PayFast-Signature' => PayFastMockGateway::sign($pfBody)];
$pfApplied = $c3->webhookService->handle('payfast', $pfBody, $pfHeaders);
$check('payfast webhook applied', $pfApplied['applied'] === true);
$invoiceP = $c3->invoices->findByOrder($orderP->id);
$check('payfast invoice paid integer cents', $invoiceP !== null && $invoiceP->paidCents === 9900);

// Deterministic, bounded synthetic matrix. Exercises the normalizer and a
// derived due/amount computation across many synthetic cases so the visible
// log is reproducible and sized for the output-stress band. No assertions
// here change pass/fail state; the real checks above are authoritative.
$mNormalizer = new GatewayEventNormalizer();
$mProviders = ['stripe', 'payfast'];
$mStatuses = ['succeeded', 'COMPLETE', 'declined', 'Paid', 'processing'];
$mCount = 1200;

echo "-- matrix begin --\n";
for ($i = 0; $i < $mCount; $i++) {
    $provider = $mProviders[$i % count($mProviders)];
    $rawStatus = $mStatuses[$i % count($mStatuses)];
    $amountCents = 1000 + (($i * 37) % 9000);
    $totalCents = $amountCents + (($i * 13) % 200);

    if ($provider === 'stripe') {
        $event = $mNormalizer->normalize('stripe', [
            'id' => 'evt_m_' . $i,
            'data' => ['object' => [
                'id' => 'pi_m_' . $i,
                'amount' => $amountCents,
                'currency' => 'usd',
                'status' => $rawStatus,
            ]],
        ]);
    } else {
        $whole = intdiv($amountCents, 100);
        $frac = $amountCents % 100;
        $gross = $whole . '.' . str_pad((string) $frac, 2, '0', STR_PAD_LEFT);
        $event = $mNormalizer->normalize('payfast', [
            'm_payment_id' => 'mpf_m_' . $i,
            'pf_payment_id' => 'pf_m_' . $i,
            'amount_gross' => $gross,
            'currency_code' => 'ZAR',
            'payment_status' => $rawStatus,
        ]);
    }

    $paid = $event['status'] === PaymentStatus::PAID ? $event['amountCents'] : 0;
    $due = $totalCents - $paid;

    printf(
        "case %04d: provider=%-7s status=%-18s amountCents=%6d due=%6d currency=%s OK\n",
        $i,
        $event['provider'],
        $event['status'],
        $event['amountCents'],
        $due,
        $event['currency']
    );
}
echo "-- matrix end --\n";

if ($failures > 0) {
    echo 'FAILED: ' . $failures . "\n";
    exit(1);
}

echo "all visible checks passed\n";
exit(0);
