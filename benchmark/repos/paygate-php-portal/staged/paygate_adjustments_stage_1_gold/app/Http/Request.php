<?php

declare(strict_types=1);

namespace App\Http;

final class Request
{
    public string $method;
    public string $path;

    /** @var array<string, mixed> */
    public array $headers;

    public string $rawBody;

    /** @var array<string, mixed> */
    public array $query;

    /**
     * @param array<string, mixed> $headers
     * @param array<string, mixed> $query
     */
    public function __construct(
        string $method,
        string $path,
        array $headers = [],
        string $rawBody = '',
        array $query = []
    ) {
        $this->method = strtoupper($method);
        $this->path = $path;
        $this->headers = $headers;
        $this->rawBody = $rawBody;
        $this->query = $query;
    }

    public function header(string $name): ?string
    {
        $target = strtolower($name);

        foreach ($this->headers as $key => $value) {
            if (strtolower((string) $key) === $target) {
                return is_array($value) ? (string) reset($value) : (string) $value;
            }
        }

        return null;
    }

    /**
     * @return array<string, mixed>
     */
    public function jsonBody(): array
    {
        $decoded = json_decode($this->rawBody, true);

        return is_array($decoded) ? $decoded : [];
    }
}
