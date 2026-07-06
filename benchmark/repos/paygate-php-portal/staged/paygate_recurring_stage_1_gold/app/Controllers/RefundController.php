<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Http\Request;
use App\Http\Response;
use App\Services\RefundService;
use DomainException;

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
