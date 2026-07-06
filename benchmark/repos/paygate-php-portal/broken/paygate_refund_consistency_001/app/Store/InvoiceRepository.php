<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\Invoice;

final class InvoiceRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function save(Invoice $invoice): void
    {
        $this->db->invoices[$invoice->id] = $invoice;
    }

    public function find(string $id): ?Invoice
    {
        return $this->db->invoices[$id] ?? null;
    }

    public function findByOrder(string $orderId): ?Invoice
    {
        foreach ($this->db->invoices as $invoice) {
            if ($invoice->orderId === $orderId) {
                return $invoice;
            }
        }

        return null;
    }

    /**
     * @return array<int, Invoice>
     */
    public function all(): array
    {
        return array_values($this->db->invoices);
    }
}
