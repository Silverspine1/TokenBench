<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Http\Request;
use App\Http\Response;
use App\Services\WebhookService;

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
