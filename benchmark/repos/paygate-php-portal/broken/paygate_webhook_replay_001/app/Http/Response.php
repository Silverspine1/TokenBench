<?php

declare(strict_types=1);

namespace App\Http;

final class Response
{
    public int $status;
    public string $body;

    /** @var array<string, string> */
    public array $headers;

    /**
     * @param array<string, string> $headers
     */
    public function __construct(int $status, string $body, array $headers = [])
    {
        $this->status = $status;
        $this->body = $body;
        $this->headers = $headers;
    }

    /**
     * @param mixed $data
     */
    public static function json($data, int $status = 200): self
    {
        return new self(
            $status,
            (string) json_encode($data, JSON_THROW_ON_ERROR),
            ['Content-Type' => 'application/json']
        );
    }

    public static function text(string $body, int $status = 200): self
    {
        return new self($status, $body, ['Content-Type' => 'text/plain']);
    }

    public function status(): int
    {
        return $this->status;
    }

    public function body(): string
    {
        return $this->body;
    }
}
