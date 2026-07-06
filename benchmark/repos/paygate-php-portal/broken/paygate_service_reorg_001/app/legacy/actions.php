<?php

declare(strict_types=1);

// Flattened request/response actions. The checkout, webhook, and refund
// controllers were bundled into this single catch-all file during a legacy
// import. These classes sit off the PSR-4 path, so the autoloader cannot find
// them; app/bootstrap.php loads this file explicitly until the actions are
// reorganized into thin per-responsibility controllers.

namespace App\Controllers {

    use App\Domain\Cart;
    use App\Http\Request;
    use App\Http\Response;
    use App\Services\CheckoutService;
    use App\Services\RefundService;
    use App\Services\WebhookService;
    use DomainException;

    final class CheckoutController
    {
        private CheckoutService $checkout;

        public function __construct(CheckoutService $checkout)
        {
            $this->checkout = $checkout;
        }

        public function create(Request $request): Response
        {
            $body = $request->jsonBody();
            $sessionId = (string) ($body['sessionId'] ?? '');
            $cartData = $body['cart'] ?? [];

            $cart = new Cart(
                (string) ($cartData['id'] ?? ''),
                (string) ($cartData['currency'] ?? 'USD'),
                is_array($cartData['items'] ?? null) ? $cartData['items'] : []
            );

            $order = $this->checkout->checkout($sessionId, $cart);

            return Response::json([
                'orderId' => $order->id,
                'status' => $order->status,
                'totalCents' => $order->totalCents,
                'currency' => $order->currency,
            ]);
        }
    }

    final class WebhookController
    {
        private WebhookService $webhooks;

        public function __construct(WebhookService $webhooks)
        {
            $this->webhooks = $webhooks;
        }

        public function handle(Request $request, string $provider): Response
        {
            $result = $this->webhooks->handle($provider, $request->rawBody, $request->headers);

            return Response::json($result, $result['applied'] ? 200 : 202);
        }
    }

    final class RefundController
    {
        private RefundService $refunds;

        public function __construct(RefundService $refunds)
        {
            $this->refunds = $refunds;
        }

        public function create(Request $request): Response
        {
            $body = $request->jsonBody();
            $paymentId = (string) ($body['paymentId'] ?? '');
            $amountCents = (int) ($body['amountCents'] ?? 0);

            try {
                $refund = $this->refunds->refund($paymentId, $amountCents);
            } catch (DomainException $e) {
                return Response::json(['error' => $e->getMessage()], 422);
            }

            return Response::json([
                'refundId' => $refund->id,
                'paymentId' => $refund->paymentId,
                'amountCents' => $refund->amountCents,
            ]);
        }
    }
}
