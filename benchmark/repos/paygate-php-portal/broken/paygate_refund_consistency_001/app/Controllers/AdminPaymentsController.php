<?php

declare(strict_types=1);

namespace App\Controllers;

use App\Http\Request;
use App\Http\Response;
use App\Services\PaymentReportService;

final class AdminPaymentsController
{
    private PaymentReportService $reports;

    public function __construct(PaymentReportService $reports)
    {
        $this->reports = $reports;
    }

    public function index(Request $request): Response
    {
        return Response::json(['rows' => $this->reports->report()]);
    }
}
