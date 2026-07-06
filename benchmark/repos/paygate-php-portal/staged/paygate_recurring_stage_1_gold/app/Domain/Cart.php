<?php

declare(strict_types=1);

namespace App\Domain;

final class Cart
{
    private string $id;
    private string $currency;

    /** @var array<int, array{sku: string, quantity: int, unitCents: int}> */
    private array $items;

    /**
     * @param array<int, array{sku: string, quantity: int, unitCents: int}> $items
     */
    public function __construct(string $id, string $currency, array $items)
    {
        $this->id = $id;
        $this->currency = strtoupper(trim($currency));
        $this->items = $items;
    }

    public function id(): string
    {
        return $this->id;
    }

    public function currency(): string
    {
        return $this->currency;
    }

    /**
     * @return array<int, array{sku: string, quantity: int, unitCents: int}>
     */
    public function items(): array
    {
        return $this->items;
    }

    public function itemsTotalCents(): int
    {
        $total = 0;

        foreach ($this->items as $item) {
            $total += ((int) $item['quantity']) * ((int) $item['unitCents']);
        }

        return $total;
    }

    public function fingerprint(): string
    {
        $normalized = [];

        foreach ($this->items as $item) {
            $normalized[] = [
                'sku' => (string) $item['sku'],
                'quantity' => (int) $item['quantity'],
                'unitCents' => (int) $item['unitCents'],
            ];
        }

        usort($normalized, static function (array $a, array $b): int {
            return strcmp($a['sku'], $b['sku']);
        });

        $payload = [
            'currency' => $this->currency,
            'items' => $normalized,
        ];

        return hash('sha256', json_encode($payload, JSON_THROW_ON_ERROR));
    }
}
