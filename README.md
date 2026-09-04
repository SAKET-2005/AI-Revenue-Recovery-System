# ReviveAI — Autonomous AI Revenue Recovery Command Center

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18%20%7C%20TypeScript-61DAFB.svg?logo=react)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg?logo=vite)](https://vitejs.dev)
[![XGBoost](https://img.shields.io/badge/XGBoost-3.2%2B-orange.svg)](https://xgboost.ai)
[![Razorpay](https://img.shields.io/badge/Razorpay-Test%20Mode%20Ready-0C2340.svg)](https://razorpay.com)
[![Tests](https://img.shields.io/badge/Tests-13%2F13%20Passing-brightgreen.svg)]()

**"An autonomous AI agent that finds slipping revenue, understands why it is at risk, chooses the safest recovery action, and executes it within strict financial guardrails."**

*Track 3: AI Revenue Recovery — Razorpay AI Buildathon 2026*

</div>

---

## 🌟 Executive Summary

Indian merchants lose 15–35% of attempted transaction volume to transient failures, network timeouts, balance issues, and authentication drops. ReviveAI transforms revenue recovery from reactive guesswork into an autonomous, bounded AI system that:

1. **Detects** slipping revenue at the transaction level.
2. **Predicts** recovery probability with an explainable XGBoost model.
3. **Diagnoses** failure root causes with contextual AI reasoning.
4. **Enforces** strict deterministic guardrails (no uncontrolled LLM money movements).
5. **Executes** bounded recovery actions (automated retries, customer nudges, payment links).
6. **Quantifies** measured money recovered and recovery lift over baseline.
7. **Maintains** an immutable audit trail for complete merchant transparency.

---

## 🏗️ Architecture: Bounded Financial Autonomy

```mermaid
flowchart LR
    A[Payment Failure] --> B[ML Recovery Model]
    B -->|P recovery| C[AI Diagnosis Agent]
    C -->|Recommended Action| D[Deterministic Policy Engine]
    D -->|Passed| E[Action Executor]
    D -->|Violation| F[Escalate to Human / Block]
    E --> G[Razorpay Test API / Simulation]
    E --> H[Immutable Audit Log]
    G --> I[Measured Money Recovered]
```

### Key Architectural Separation

| Component | Role | Guarantee |
|---|---|---|
| **AI Diagnosis Agent** | Understands context & suggests intervention | Recommends only — zero direct execution authority |
| **Policy Engine** | Deterministic guardrail evaluation | Hard business logic (amounts, retry counters, thresholds) |
| **Action Executor** | Dispatches allowed recovery actions | Razorpay Test Mode & Simulation layer isolation |
| **Audit Trail** | Logs every decision & policy evaluation | Complete compliance and auditability |

---

## 🛡️ Codified Guardrails & Policies

- **Automated Retry Ceiling**: $\le$ ₹10,000 transaction amount.
- **Retry Velocity Limit**: Maximum 2 automated retries per transaction.
- **High-Value Escalation**: Transactions > ₹50,000 are **always** routed to human review.
- **Non-Retryable Classification**: Expired cards and invalid details are **never** retried; routed to Payment Links or Nudges.
- **Confidence Gate**: AI/ML confidence < 60% triggers mandatory escalation.

---

## 🚀 Quick Start (Local Setup)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Clone & Configure
```bash
git clone https://github.com/your-username/ReviveAI.git
cd ReviveAI
cp .env.example .env
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Train the ML Recovery Model
python -m scripts.train_model

# Start FastAPI Backend (Port 8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** to access the ReviveAI Merchant Command Center.

---

## 🧪 Running Automated Tests

ReviveAI includes comprehensive test coverage for policy guardrails, ML prediction, agent reasoning, webhook idempotency, and API endpoints:

```bash
cd backend
python -m pytest tests/ -v
```

All 13 automated tests run and validate the core safety invariants:
```
tests/test_policy_engine.py::test_high_value_transaction_is_escalated PASSED
tests/test_policy_engine.py::test_expired_card_is_not_retried PASSED
tests/test_policy_engine.py::test_retry_limit_is_enforced PASSED
tests/test_policy_engine.py::test_low_confidence_is_escalated PASSED
tests/test_policy_engine.py::test_valid_retry_is_allowed PASSED
tests/test_policy_engine.py::test_payment_link_allowed_within_probability_band PASSED
tests/test_webhooks_and_api.py::test_webhook_idempotency_and_duplicate_rejection PASSED
...
```

---

## ⚡ Demo Walkthrough (5-Minute Hackathon Pitch)

See [`docs/demo.md`](docs/demo.md) for the complete presenter pitch guide.

1. **Dashboard**: Inspect real-time metrics (Revenue at Risk, Recovered, Recovery Funnel).
2. **Transaction Queue**: Open a failed payment (`TXN_000996`) $\to$ View 91% recovery probability, AI reasoning, and approved policy check.
3. **Guardrails**: Inspect a high-value payment (>₹50,000) $\to$ Observe deterministic human escalation.
4. **Batch Evaluation**: Trigger batch recovery in Demo Controls $\to$ Compare ReviveAI vs baseline lift (+30%+ improvement).
5. **Payment Link**: Generate and complete a recovery payment link in the simulated checkout modal.

---

## 📂 Project Structure

```
ReviveAI/
├── backend/
│   ├── app/
│   │   ├── api/            # REST Endpoints (Dashboard, Transactions, Recovery, Webhooks, Audit)
│   │   ├── agents/         # AI Recovery Agent & Deterministic Fallbacks
│   │   ├── executors/      # Action Execution Layer
│   │   ├── integrations/   # PaymentProvider (Razorpay Test Mode & Mock)
│   │   ├── ml/             # XGBoost Predictor & Training Pipeline
│   │   ├── models/         # SQLAlchemy ORM Models
│   │   ├── policies/       # Deterministic Guardrail Engine (PolicyEngine)
│   │   └── schemas/        # Pydantic Schemas & Types
│   ├── tests/              # Pytest Suite
│   └── ml_artifacts/       # Serialized XGBoost Model & Encoders
├── frontend/
│   ├── src/
│   │   ├── components/     # Sidebar, MetricCards, Modals
│   │   ├── pages/          # Dashboard, Transactions, Detail, Audit, Evaluation, Demo
│   │   └── services/       # API Client
├── docs/
│   ├── architecture.md     # In-depth architectural design & Mermaid diagrams
│   ├── api.md              # Complete REST API specifications
│   └── demo.md             # 5-minute hackathon pitch script
├── scripts/
│   ├── train_model.py      # ML Model Training Script
│   ├── seed_database.py    # Synthetic Data Seeding
│   └── run_demo.py         # CLI Interactive Demo Runner
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 📄 License & Disclaimer

Built for the **Razorpay AI Buildathon 2026**. All demo datasets use synthetic, non-PII transaction records. Razorpay APIs operate strictly in test mode.
