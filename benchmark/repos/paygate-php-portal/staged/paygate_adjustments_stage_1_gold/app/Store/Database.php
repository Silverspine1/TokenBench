<?php

declare(strict_types=1);

namespace App\Store;

final class Database
{
    /** @var array<string, \App\Domain\Order> */
    public array $orders = [];

    /** @var array<string, \App\Domain\Invoice> */
    public array $invoices = [];

    /** @var array<string, \App\Domain\Payment> */
    public array $payments = [];

    /** @var array<string, \App\Domain\Refund> */
    public array $refunds = [];

    /** @var array<string, \App\Domain\Adjustment> */
    public array $adjustments = [];

    /** @var array<string, bool> */
    public array $idempotency = [];

    /** @var array<string, string> */
    public array $orderFingerprints = [];

    /** @var array<string, array<int, string>> */
    public array $sessionOrders = [];

    private int $counter = 0;

    public function nextId(string $prefix): string
    {
        $this->counter++;

        return $prefix . '_' . $this->counter;
    }
}
