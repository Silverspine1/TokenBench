<?php

declare(strict_types=1);

namespace App;

use App\Controllers\AdminPaymentsController;
use App\Controllers\CheckoutController;
use App\Controllers\RefundController;
use App\Controllers\WebhookController;
use App\Payment\GatewayEventNormalizer;
use App\Payment\PayFastMockGateway;
use App\Payment\StripeMockGateway;
use App\Payment\WebhookVerifier;
use App\Services\AdjustmentService;
use App\Services\CheckoutService;
use App\Services\IdempotencyService;
use App\Services\InvoiceService;
use App\Services\PaymentReportService;
use App\Services\RefundService;
use App\Services\WebhookService;
use App\Store\AdjustmentRepository;
use App\Store\Database;
use App\Store\IdempotencyRepository;
use App\Store\InvoiceRepository;
use App\Store\OrderRepository;
use App\Store\PaymentRepository;
use App\Store\RefundRepository;

final class Container
{
    public Database $db;
    public OrderRepository $orders;
    public PaymentRepository $payments;
    public InvoiceRepository $invoices;
    public RefundRepository $refunds;
    public AdjustmentRepository $adjustmentsRepo;
    public IdempotencyRepository $idempotencyRepo;

    public StripeMockGateway $stripe;
    public PayFastMockGateway $payfast;
    public WebhookVerifier $verifier;
    public GatewayEventNormalizer $normalizer;

    public IdempotencyService $idempotency;
    public CheckoutService $checkout;
    public InvoiceService $invoiceService;
    public AdjustmentService $adjustmentService;
    public RefundService $refundService;
    public WebhookService $webhookService;
    public PaymentReportService $reportService;

    public CheckoutController $checkoutController;
    public WebhookController $webhookController;
    public RefundController $refundController;
    public AdminPaymentsController $adminController;

    public function __construct()
    {
        $this->db = new Database();
        $this->orders = new OrderRepository($this->db);
        $this->payments = new PaymentRepository($this->db);
        $this->invoices = new InvoiceRepository($this->db);
        $this->refunds = new RefundRepository($this->db);
        $this->adjustmentsRepo = new AdjustmentRepository($this->db);
        $this->idempotencyRepo = new IdempotencyRepository($this->db);

        $this->stripe = new StripeMockGateway();
        $this->payfast = new PayFastMockGateway();
        $this->verifier = new WebhookVerifier([
            $this->stripe->name() => $this->stripe,
            $this->payfast->name() => $this->payfast,
        ]);
        $this->normalizer = new GatewayEventNormalizer();

        $this->idempotency = new IdempotencyService($this->idempotencyRepo);
        $this->checkout = new CheckoutService($this->db, $this->orders, $this->invoices);
        $this->invoiceService = new InvoiceService($this->invoices, $this->payments, $this->refunds, $this->orders, $this->adjustmentsRepo);
        $this->adjustmentService = new AdjustmentService($this->db, $this->adjustmentsRepo, $this->orders);
        $this->refundService = new RefundService($this->db, $this->payments, $this->refunds, $this->invoices, $this->orders);
        $this->webhookService = new WebhookService(
            $this->db,
            $this->verifier,
            $this->normalizer,
            $this->payments,
            $this->invoices,
            $this->orders,
            $this->idempotency
        );
        $this->reportService = new PaymentReportService($this->orders, $this->payments, $this->refunds, $this->invoices);

        $this->checkoutController = new CheckoutController($this->checkout);
        $this->webhookController = new WebhookController($this->webhookService);
        $this->refundController = new RefundController($this->refundService);
        $this->adminController = new AdminPaymentsController($this->reportService);
    }
}
