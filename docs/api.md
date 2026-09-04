# ReviveAI — REST API Documentation

Base URL: `http://localhost:8000/api`

---

## 1. System Health

### `GET /health`
Returns operational health, active mode, and component status.

**Response `200 OK`**:
```json
{
  "status": "ok",
  "mode": "demo",
  "llm_available": false,
  "razorpay_available": false,
  "ml_model_loaded": true,
  "database": "connected",
  "version": "1.0.0"
}
```

---

## 2. Dashboard & Analytics

### `GET /dashboard/metrics`
Aggregated real-time metrics across all transactions.

**Response `200 OK`**:
```json
{
  "total_transactions": 1000,
  "revenue_processed": 3118601.72,
  "failed_transactions": 322,
  "revenue_at_risk": 1106782.88,
  "revenue_recovered": 425600.0,
  "recovery_rate": 38.45,
  "automated_recoveries": 94,
  "human_escalations": 53,
  "policy_blocks": 33,
  "avg_recovery_probability": 0.6842,
  "recovery_by_failure_type": {
    "temporary_bank_failure": { "count": 62, "amount": 284000.0 }
  },
  "recovery_funnel": {
    "at_risk": 322,
    "diagnosed": 322,
    "intervention": 241,
    "attempted": 241,
    "recovered": 94
  }
}
```

---

## 3. Transactions

### `GET /transactions`
List transactions with optional filtering and pagination.

**Query Parameters:**
- `status`: Filter by `failed`, `recovered`, `success`, `pending`
- `limit`: Number of records (default: 50, max: 500)
- `offset`: Pagination offset

### `GET /transactions/{transaction_id}`
Retrieve complete transaction details, customer history, ML predictions, AI diagnosis, and audit log.

### `POST /transactions/generate`
Generate synthetic transactions for testing.

**Request Body**:
```json
{
  "count": 1000
}
```

---

## 4. Recovery Operations

### `POST /recovery/analyze/{transaction_id}`
Executes the risk analysis, ML prediction, AI diagnosis, and guardrail check.

### `POST /recovery/execute/{transaction_id}`
Executes the approved recovery action via the active payment provider.

### `POST /recovery/run-batch`
Runs the complete autonomous recovery pipeline over all failed transactions and records batch evaluation metrics.

**Request Body**:
```json
{
  "limit": null
}
```

---

## 5. Webhooks & Payment Links

### `POST /webhooks/razorpay`
Ingests Razorpay webhook events with signature verification and deduplication.

### `POST /payment-links/create`
Generates a recovery payment link.

### `POST /payment-links/complete/{link_id}`
Simulates or completes customer payment for a recovery payment link.

---

## 6. Audit & Evaluations

### `GET /audit-log`
Query the immutable audit trail filtered by event type or transaction ID.

### `GET /evaluation`
Retrieve historical batch recovery evaluation runs with baseline comparison metrics.

### `GET /ml/metrics`
Retrieve ML model evaluation metrics (ROC-AUC, Precision, Recall, F1, Feature Importances).
