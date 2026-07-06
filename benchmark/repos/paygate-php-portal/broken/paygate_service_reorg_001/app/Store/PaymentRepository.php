<?php

declare(strict_types=1);

namespace App\Store;

use App\Domain\Payment;

final class PaymentRepository
{
    private Database $db;

    public function __construct(Database $db)
    {
        $this->db = $db;
    }

    public function save(Payment $payment): void
    {
        $this->db->payments[$payment->id] = $payment;
    }

    public function find(string $id): ?Payment
    {
        return $this->db->payments[$id] ?? null;
    }

    public function findByReference(string $reference): ?Payment
    {
        foreach ($this->db->payments as $payment) {
            if ($payment->paymentReference === $reference) {
                return $payment;
            }
        }

        return null;
    }

    /**
     * @return array<int, Payment>
     */
    public function findByOrder(string $orderId): array
    {
        $result = [];

        foreach ($this->db->payments as $payment) {
            if ($payment->orderId === $orderId) {
                $result[] = $payment;
            }
        }

        return $result;
    }

    /**
     * @return array<int, Payment>
     */
    public function all(): array
    {
        return array_values($this->db->payments);
    }
}
