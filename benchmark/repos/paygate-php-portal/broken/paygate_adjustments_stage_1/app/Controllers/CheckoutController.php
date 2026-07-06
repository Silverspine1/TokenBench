<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Domain\Cart;
use App\Http\Request;
use App\Http\Response;
use App\Services\CheckoutService;

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
