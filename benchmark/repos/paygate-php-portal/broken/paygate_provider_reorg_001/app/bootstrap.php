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

// Legacy provider code was flattened into these catch-all files during an
// import. They do not sit at PSR-4 paths, so the autoloader cannot find them;
// load them explicitly here until the provider code is reorganized into proper
// App\Payment\* modules.
foreach ([
    __DIR__ . '/legacy/z_provider.php',
    __DIR__ . '/legacy/a.php',
    __DIR__ . '/legacy/b.php',
    __DIR__ . '/misc/pay_ops.php',
] as $legacyFile) {
    if (is_file($legacyFile)) {
        require $legacyFile;
    }
}
