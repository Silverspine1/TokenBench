<?php

declare(strict_types=1);

$ws = getenv('TOKENBENCH_WORKSPACE') ?: getenv('WORKSPACE');
require $ws . '/app/bootstrap.php';

use App\Container;
use App\Domain\PaymentStatus;
use App\Payment\GatewayEventNormalizer;
use App\Payment\StripeMockGateway;

$n = new GatewayEventNormalizer();
$results = [];

$expectedKeys = ['provider', 'eventId', 'paymentReference', 'status', 'amountCents', 'currency'];

/** True when $event has exactly the six documented keys. */
function hasExactKeys(array $event, array $expected): bool
{
    $keys = array_keys($event);
    sort($keys);
    $exp = $expected;
    sort($exp);

    return $keys === $exp;
}

// --- newer Stripe-style payload ---
$ev = $n->normalize('stripe', [
    'id' => 'evt_ns',
    'data' => ['object' => ['id' => 'pi_ns', 'amount' => 2234, 'currency' => 'usd', 'status' => 'paid']],
]);
$results['new_stripe_payload'] =
    hasExactKeys($ev, $expectedKeys)
    && $ev['eventId'] === 'evt_ns'
    && $ev['paymentReference'] === 'pi_ns'
    && $ev['amountCents'] === 2234
    && $ev['status'] === PaymentStatus::PAID
    && $ev['currency'] === 'USD';

// --- older Stripe-style payload ---
$ev = $n->normalize('stripe', [
    'event_id' => 'evt_os',
    'payment_ref' => 'pi_os',
    'amount_cents' => 500,
    'currency' => 'USD',
    'status' => 'Paid',
]);
$results['old_stripe_payload'] =
    hasExactKeys($ev, $expectedKeys)
    && $ev['eventId'] === 'evt_os'
    && $ev['paymentReference'] === 'pi_os'
    && $ev['amountCents'] === 500
    && $ev['status'] === PaymentStatus::PAID;

// --- newer PayFast-style payload ---
$ev = $n->normalize('payfast', [
    'm_payment_id' => 'mpf_np',
    'pf_payment_id' => 'pf_np',
    'amount_gross' => '99.00',
    'currency_code' => 'ZAR',
    'payment_status' => 'paid',
]);
$results['new_payfast_payload'] =
    hasExactKeys($ev, $expectedKeys)
    && $ev['eventId'] === 'mpf_np'
    && $ev['paymentReference'] === 'pf_np'
    && $ev['amountCents'] === 9900
    && $ev['status'] === PaymentStatus::PAID
    && $ev['currency'] === 'ZAR';

// --- older PayFast-style payload ---
$ev = $n->normalize('payfast', [
    'payment_id' => 'mpf_op',
    'reference' => 'pf_op',
    'amount' => '12.34',
    'currency' => 'ZAR',
    'status' => 'completed',
]);
$results['old_payfast_payload'] =
    hasExactKeys($ev, $expectedKeys)
    && $ev['eventId'] === 'mpf_op'
    && $ev['paymentReference'] === 'pf_op'
    && $ev['amountCents'] === 1234
    && $ev['status'] === PaymentStatus::PAID;

// --- mixed-casing status values are canonicalised ---
$a = $n->normalize('stripe', [
    'id' => 'evt_c1',
    'data' => ['object' => ['id' => 'pi_c1', 'amount' => 100, 'currency' => 'usd', 'status' => 'SUCCEEDED']],
]);
$b = $n->normalize('payfast', [
    'm_payment_id' => 'mpf_c2',
    'pf_payment_id' => 'pf_c2',
    'amount_gross' => '1.00',
    'currency_code' => 'ZAR',
    'payment_status' => 'Complete',
]);
$d = $n->normalize('stripe', [
    'id' => 'evt_c3',
    'data' => ['object' => ['id' => 'pi_c3', 'amount' => 100, 'currency' => 'usd', 'status' => 'Declined']],
]);
$results['mixed_status_casing'] =
    $a['status'] === PaymentStatus::PAID
    && $b['status'] === PaymentStatus::PAID
    && $d['status'] === PaymentStatus::FAILED;

// --- invalid signatures are rejected before any state change ---
$c = new Container();
$body = json_encode([
    'id' => 'evt_sig',
    'data' => ['object' => ['id' => 'pi_sig', 'amount' => 100, 'currency' => 'usd', 'status' => 'succeeded']],
], JSON_THROW_ON_ERROR);
$res = $c->webhookService->handle('stripe', $body, ['Stripe-Signature' => 'deadbeef']);
$results['invalid_signature_rejected'] =
    $res['applied'] === false
    && $res['reason'] === 'invalid_signature'
    && $c->payments->findByReference('pi_sig') === null;

echo json_encode($results);
exit(0);
