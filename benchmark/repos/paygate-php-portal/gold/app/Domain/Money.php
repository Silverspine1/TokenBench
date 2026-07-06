<?php

declare(strict_types=1);

namespace App\Domain;

use InvalidArgumentException;

final class Money
{
    private int $cents;
    private string $currency;

    private function __construct(int $cents, string $currency)
    {
        $this->cents = $cents;
        $this->currency = strtoupper(trim($currency));
    }

    public static function fromCents(int $cents, string $currency): self
    {
        return new self($cents, $currency);
    }

    public static function fromDecimalString(string $amount, string $currency): self
    {
        $trimmed = trim($amount);
        $negative = false;

        if ($trimmed !== '' && ($trimmed[0] === '-' || $trimmed[0] === '+')) {
            $negative = $trimmed[0] === '-';
            $trimmed = substr($trimmed, 1);
        }

        if ($trimmed === '' || !preg_match('/^\d+(\.\d+)?$/', $trimmed)) {
            throw new InvalidArgumentException('Invalid decimal amount: ' . $amount);
        }

        $parts = explode('.', $trimmed);
        $whole = $parts[0];
        $fraction = $parts[1] ?? '';

        $fraction = substr($fraction . '00', 0, 2);

        $cents = ((int) $whole) * 100 + (int) $fraction;

        if ($negative) {
            $cents = -$cents;
        }

        return new self($cents, $currency);
    }

    public function cents(): int
    {
        return $this->cents;
    }

    public function currency(): string
    {
        return $this->currency;
    }

    public function add(self $o): self
    {
        $this->assertSameCurrency($o);

        return new self($this->cents + $o->cents, $this->currency);
    }

    public function subtract(self $o): self
    {
        $this->assertSameCurrency($o);

        return new self($this->cents - $o->cents, $this->currency);
    }

    public function toDecimalString(): string
    {
        $negative = $this->cents < 0;
        $abs = $negative ? -$this->cents : $this->cents;

        $whole = intdiv($abs, 100);
        $fraction = $abs % 100;

        $result = $whole . '.' . str_pad((string) $fraction, 2, '0', STR_PAD_LEFT);

        return $negative ? '-' . $result : $result;
    }

    public function equals(self $o): bool
    {
        return $this->cents === $o->cents && $this->currency === $o->currency;
    }

    private function assertSameCurrency(self $o): void
    {
        if ($this->currency !== $o->currency) {
            throw new InvalidArgumentException(
                'Currency mismatch: ' . $this->currency . ' vs ' . $o->currency
            );
        }
    }
}
