<?php

declare(strict_types=1);

spl_autoload_register(static function (string $class): void {
    $prefix = 'App\\';
    $baseDir = __DIR__ . DIRECTORY_SEPARATOR;

    if (strncmp($class, $prefix, strlen($prefix)) !== 0) {
        return;
    }

    $relative = substr($class, strlen($prefix));
    $relativePath = str_replace('\\', DIRECTORY_SEPARATOR, $relative);
    $file = $baseDir . $relativePath . '.php';

    if (is_file($file)) {
        require $file;
    }
});

// Payment flow logic (checkout, webhook handling, refunds) and its
// request/response actions were flattened into these catch-all files during a
// legacy import. They do not sit at PSR-4 paths, so the autoloader cannot find
// them; load them explicitly here until the flow is reorganized into proper
// App\Services\* and App\Controllers\* classes at their canonical paths.
foreach ([
    __DIR__ . '/legacy/flow.php',
    __DIR__ . '/legacy/actions.php',
] as $legacyFile) {
    if (is_file($legacyFile)) {
        require $legacyFile;
    }
}
