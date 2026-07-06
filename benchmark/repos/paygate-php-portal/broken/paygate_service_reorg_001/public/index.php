<?php

declare(strict_types=1);

require __DIR__ . '/../app/bootstrap.php';

use App\Container;
use App\Http\Request;
use App\Http\Response;
use App\Http\Router;

$container = new Container();
$router = new Router();

$router->add('POST', '/checkout', static function (Request $request) use ($container): Response {
    return $container->checkoutController->create($request);
});

$router->add('POST', '/webhooks/stripe', static function (Request $request) use ($container): Response {
    return $container->webhookController->handle($request, 'stripe');
});

$router->add('POST', '/webhooks/payfast', static function (Request $request) use ($container): Response {
    return $container->webhookController->handle($request, 'payfast');
});

$router->add('POST', '/refunds', static function (Request $request) use ($container): Response {
    return $container->refundController->create($request);
});

$router->add('GET', '/admin/payments', static function (Request $request) use ($container): Response {
    return $container->adminController->index($request);
});

if (PHP_SAPI === 'cli') {
    return;
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
$rawBody = file_get_contents('php://input') ?: '';
$headers = function_exists('getallheaders') ? (getallheaders() ?: []) : [];

$request = new Request($method, $path, $headers, $rawBody, $_GET);
$response = $router->dispatch($request);

http_response_code($response->status);

foreach ($response->headers as $name => $value) {
    header($name . ': ' . $value);
}

echo $response->body;
