<?php

declare(strict_types=1);

namespace App\Http;

final class Router
{
    /** @var array<string, callable> */
    private array $routes = [];

    public function add(string $method, string $path, callable $handler): void
    {
        $this->routes[$this->key($method, $path)] = $handler;
    }

    public function dispatch(Request $request): Response
    {
        $key = $this->key($request->method, $request->path);

        if (!isset($this->routes[$key])) {
            return Response::text('Not Found', 404);
        }

        $handler = $this->routes[$key];
        $result = $handler($request);

        if ($result instanceof Response) {
            return $result;
        }

        return Response::text((string) $result, 200);
    }

    private function key(string $method, string $path): string
    {
        return strtoupper($method) . ' ' . $path;
    }
}
