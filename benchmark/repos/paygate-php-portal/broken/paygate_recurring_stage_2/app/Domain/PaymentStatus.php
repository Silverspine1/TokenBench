<?php

declare(strict_types=1);

namespace App\Domain;

final class PaymentStatus
{
    public const PENDING = 'pending';
    public const PAID = 'paid';
    public const FAILED = 'failed';
    public const REFUNDED = 'refunded';
    public const PARTIALLY_REFUNDED = 'partially_refunded';

    public static function normalize(string $raw): string
    {
        $value = strtolower(trim($raw));

        $paidVariants = ['paid', 'completed', 'succeeded', 'success', 'complete'];
        $failedVariants = ['failed', 'declined', 'failure', 'error'];
        $refundedVariants = ['refunded'];
        $partialVariants = ['partially_refunded', 'partial_refund'];
        $pendingVariants = ['pending', 'processing', 'created'];

        if (in_array($value, $paidVariants, true)) {
            return self::PAID;
        }

        if (in_array($value, $failedVariants, true)) {
            return self::FAILED;
        }

        if (in_array($value, $refundedVariants, true)) {
            return self::REFUNDED;
        }

        if (in_array($value, $partialVariants, true)) {
            return self::PARTIALLY_REFUNDED;
        }

        if (in_array($value, $pendingVariants, true)) {
            return self::PENDING;
        }

        return $value;
    }
}
