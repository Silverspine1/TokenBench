<?php

declare(strict_types=1);

// Legacy import dump (misc). A grab-bag of payment-adjacent helpers that were
// left behind by the migration. Nothing here is on a PSR-4 path; bootstrap
// loads it explicitly. Kept only so existing requires do not fatal.

namespace App\Legacy;

/**
 * Provider name aliases that an older integration used. Unused by the current
 * flows but retained to avoid breaking any straggling caller.
 *
 * @return array<string, string>
 */
function legacy_provider_aliases(): array
{
    return [
        'stripe_v1' => 'stripe',
        'payfast_classic' => 'payfast',
    ];
}
