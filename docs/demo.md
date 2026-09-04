# ReviveAI — 5-Minute Pitch & Demo Script

> **Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

---

## 🎯 The Hook (Minute 0:00 - 0:45)

> *"Every day, Indian merchants lose millions of rupees to failed payments. But here's the reality: not all failed payments are truly lost. Many are transient bank timeouts, temporary network drops, or recoverable balance issues.*
>
> *Today, merchants either do nothing—losing that revenue forever—or blindly spam retries, which damages customer trust, drives up payment gateway decline fees, and risks chargebacks.*
>
> *Meet **ReviveAI**: an autonomous AI agent that finds slipping revenue, understands why it is at risk, chooses the safest recovery action, and executes it within strict financial guardrails."*

---

## 📊 Step 1: Merchant Command Center (Minute 0:45 - 1:30)

1. Open the **Dashboard** at `http://localhost:5173`.
2. Point to the top KPIs:
   - **Total Transactions Processed**: ₹31.2L across 1,000 transactions.
   - **Revenue at Risk**: ₹11.1L in failed payments.
   - **Revenue Recovered**: ₹4.25L already saved.
3. Highlight the **Recovery Funnel** and **Recovery by Failure Type** charts:
   - *"Notice how ReviveAI categorizes failures—temporary bank failures, insufficient funds, network timeouts, expired cards."*

---

## 🔍 Step 2: Individual Recovery Pipeline & Bounded Autonomy (Minute 1:30 - 2:45)

1. Navigate to **Transaction Queue**.
2. Click on a failed transaction with transient timeout:
   - **Transaction ID**: `TXN_000996`
   - **Failure Reason**: Bank Timeout (Transient)
   - **ML Recovery Probability**: **91%**
   - **AI Diagnosis**: *"Transient banking infrastructure failure with high historical recovery likelihood."*
   - **AI Recommended Action**: `Retry Payment`
   - **Deterministic Guardrails**:
     - ✅ Amount limit (₹4,500 $\le$ ₹10,000)
     - ✅ Retry limit (0 of 2 used)
     - ✅ Confidence threshold (94% $\ge$ 60%)
     - ✅ Failure type is retryable
     - **Status: APPROVED**
3. Click **Execute Recovery**:
   - Watch the transaction transition to **Recovered**.
   - Show the **Audit Trail** appending the immutable decision log.

---

## 🛑 Step 3: Guardrails in Action — Bounded Financial Autonomy (Minute 2:45 - 3:30)

1. Open a high-value or expired card transaction (e.g. ₹58,000 or Expired Card).
2. Point out the policy decision:
   - *"Even if the AI wanted to retry, our **Deterministic Policy Engine** blocks it."*
   - *"High-value transactions (>₹50,000) are automatically **Escalated to Human Review**."*
   - *"Expired cards are **Blocked from Retrying** and routed to a Payment Link / Nudge."*
   - **Key takeaway for judges**: *"The LLM cannot hallucinate or directly move funds. The policy engine is deterministic code."*

---

## 🚀 Step 4: Batch Autonomous Recovery & ROI (Minute 3:30 - 4:30)

1. Navigate to **Demo Controls** & click **"Run Recovery Agent (All Failed)"**.
2. Watch the live batch processor analyze all failed payments.
3. Switch to **Recovery Evaluation**:
   - **Baseline (No AI / Dumb Retry)**: ₹1.42L recovered (12.8% recovery rate).
   - **ReviveAI Autonomous Recovery**: **₹4.85L recovered (43.8% recovery rate)**.
   - **Recovery Lift**: **+31.0% net improvement in captured revenue**.

---

## 🏁 Conclusion & Wrap-up (Minute 4:30 - 5:00)

> *"ReviveAI bridges the gap between AI intelligence and strict financial safety. By combining explainable machine learning, LLM diagnostics, and deterministic guardrails, we deliver measured revenue recovery that merchants can trust.*
>
> *Thank you, and we're ready for your questions!"*
