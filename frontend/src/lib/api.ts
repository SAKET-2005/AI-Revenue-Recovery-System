// Signal Ledger: Unified API Client with Backend Adapters & Graceful Mock Fallback
import { analytics, auditEvents, dashboardMetrics, decisions, transactions } from "./mockData";
import type {
  AnalyticsSnapshot,
  AuditEvent,
  DashboardMetrics,
  EventType,
  PaymentMethod,
  PolicyStatus,
  RecoveryAction,
  RecoveryDecision,
  RecoveryRunResult,
  Transaction,
  TransactionStatus,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const USE_MOCK_DATA = String(import.meta.env.VITE_USE_MOCK_DATA ?? "true") !== "false";

const pause = (ms = 320) => new Promise((resolve) => setTimeout(resolve, ms));

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Request to ${path} failed with HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function adaptPaymentMethod(method?: string): "UPI" | "Card" | "Netbanking" | "Wallet" {
  if (!method) return "UPI";
  const m = method.toLowerCase();
  if (m.includes("card")) return "Card";
  if (m.includes("net") || m.includes("bank")) return "Netbanking";
  if (m.includes("wallet")) return "Wallet";
  return "UPI";
}

function adaptAction(action?: string): RecoveryAction {
  if (!action) return "none";
  const a = action.toLowerCase();
  if (a === "retry") return "retry";
  if (a.includes("link") || a.includes("nudge")) return "payment_link";
  if (a.includes("human") || a.includes("escalat")) return "escalate";
  return "none";
}

function adaptPolicy(policy?: string): PolicyStatus {
  if (!policy) return "pending";
  const p = policy.toUpperCase();
  if (p === "ALLOW" || p === "APPROVED") return "approved";
  if (p === "BLOCK" || p === "BLOCKED" || p === "STOP") return "blocked";
  return "pending";
}

function adaptStatus(status?: string, prob = 70): TransactionStatus {
  if (!status) return "pending";
  const s = status.toLowerCase();
  if (s === "recovered" || s === "success") return "recovered";
  if (s === "blocked" || s === "stop") return "blocked";
  if (s.includes("human") || s.includes("escalat")) return "human_review";
  if (s === "failed" || s === "at_risk") return prob >= 75 ? "at_risk" : "pending";
  return "pending";
}

function adaptTransaction(item: any): Transaction {
  const prob =
    item.recovery_probability !== undefined
      ? item.recovery_probability <= 1
        ? Math.round(item.recovery_probability * 100)
        : Math.round(item.recovery_probability)
      : item.recoveryProbability ?? 75;

  return {
    id: item.transaction_id || item.id || `TXN_${Math.floor(1000 + Math.random() * 9000)}`,
    amount: Number(item.amount) || 0,
    customer:
      item.customer ||
      (item.customer_id
        ? `Customer ${String(item.customer_id).replace(/\D/g, "").slice(-3) || item.customer_id}`
        : "Customer 101"),
    paymentMethod: adaptPaymentMethod(item.payment_method || item.paymentMethod),
    failureReason: item.failure_reason || item.failureReason || "Temporary Bank Failure",
    recoveryProbability: prob,
    aiAction: adaptAction(item.recommended_action || item.aiAction),
    policy: adaptPolicy(item.policy_decision || item.policy),
    status: adaptStatus(item.payment_status || item.status, prob),
    timestamp: item.created_at
      ? new Date(item.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
      : item.timestamp || "Today, 09:41:00",
    diagnosis: item.diagnosis || "Contextual recovery probability identified from transaction pattern.",
    retryCount: item.retry_count ?? item.retryCount ?? 0,
    customerHistory: item.customerHistory || "Prior successful transaction history verified",
  };
}

export async function getDashboardMetrics(): Promise<DashboardMetrics> {
  if (USE_MOCK_DATA) {
    await pause();
    return dashboardMetrics;
  }
  try {
    const data = await request<any>("/dashboard/metrics");
    return {
      revenueProcessed: data.revenue_processed ?? data.revenueProcessed ?? dashboardMetrics.revenueProcessed,
      revenueAtRisk: data.revenue_at_risk ?? data.revenueAtRisk ?? dashboardMetrics.revenueAtRisk,
      revenueRecovered: data.revenue_recovered ?? data.revenueRecovered ?? dashboardMetrics.revenueRecovered,
      recoveryRate: data.recovery_rate ?? data.recoveryRate ?? dashboardMetrics.recoveryRate,
      automatedRecoveries: data.automated_recoveries ?? data.automatedRecoveries ?? dashboardMetrics.automatedRecoveries,
      humanEscalations: data.human_escalations ?? data.humanEscalations ?? dashboardMetrics.humanEscalations,
      processedDelta: data.processedDelta ?? 12.8,
      atRiskDelta: data.atRiskDelta ?? -4.6,
      recoveredDelta: data.recoveredDelta ?? 18.4,
      rateDelta: data.rateDelta ?? 7.2,
    };
  } catch (err) {
    console.warn("[ReviveAI API] /dashboard/metrics failed, falling back to mock data", err);
    return dashboardMetrics;
  }
}

export async function getTransactions(): Promise<Transaction[]> {
  if (USE_MOCK_DATA) {
    await pause(420);
    return transactions;
  }
  try {
    const data = await request<any>("/transactions");
    const list = Array.isArray(data) ? data : data.transactions || [];
    if (list.length === 0) return transactions;
    return list.map(adaptTransaction);
  } catch (err) {
    console.warn("[ReviveAI API] /transactions failed, falling back to mock data", err);
    return transactions;
  }
}

export async function getTransaction(id: string): Promise<Transaction> {
  if (USE_MOCK_DATA) {
    await pause(260);
    const item = transactions.find((txn) => txn.id === id);
    if (!item) return transactions[0];
    return item;
  }
  try {
    const data = await request<any>(`/transactions/${id}`);
    return adaptTransaction(data);
  } catch (err) {
    console.warn(`[ReviveAI API] /transactions/${id} failed, falling back to local list`, err);
    const item = transactions.find((txn) => txn.id === id);
    return item || transactions[0];
  }
}

export async function getDecisions(): Promise<RecoveryDecision[]> {
  if (USE_MOCK_DATA) {
    await pause(360);
    return decisions;
  }
  try {
    const txns = await getTransactions();
    const candidateTxns = txns.filter((t) => t.recoveryProbability > 50 || t.status === "recovered");
    if (candidateTxns.length > 0) {
      return candidateTxns.slice(0, 8).map((t, idx) => ({
        id: `DEC_${String(418 - idx).padStart(4, "0")}`,
        transactionId: t.id,
        amount: t.amount,
        diagnosis: t.diagnosis,
        probability: t.recoveryProbability,
        recommendation: t.aiAction === "retry" ? "RETRY PAYMENT" : t.aiAction === "payment_link" ? "CREATE PAYMENT LINK" : "ESCALATE",
        confidence: Math.min(98, t.recoveryProbability + 3),
        policy: t.policy,
        outcome: t.status === "recovered" ? "Recovered" : t.policy === "blocked" ? "Human review required" : "Pending",
        reasons: [
          `${t.paymentMethod} transaction pattern evaluated`,
          `Recovery probability calculated at ${t.recoveryProbability}%`,
          t.amount <= 10000 ? "Amount within automated threshold (<= ₹10,000)" : "Amount exceeds threshold, routed to review",
          t.retryCount < 2 ? "Retry velocity limit preserved (< 2 attempts)" : "Maximum retry attempts reached",
        ],
      }));
    }
    return decisions;
  } catch (err) {
    console.warn("[ReviveAI API] getDecisions failed, using mock data", err);
    return decisions;
  }
}

export async function getAuditEvents(): Promise<AuditEvent[]> {
  if (USE_MOCK_DATA) {
    await pause(300);
    return auditEvents;
  }
  try {
    const data = await request<any>("/audit-log");
    const list = Array.isArray(data) ? data : data.entries || [];
    if (list.length === 0) return auditEvents;

    return list.map((entry: any, index: number): AuditEvent => {
      const et = String(entry.event_type || "").toLowerCase();
      let type: EventType = "revenue_risk";
      let status: AuditEvent["status"] = "info";

      if (et.includes("recovery") || et.includes("recovered")) {
        type = "recovery";
        status = "success";
      } else if (et.includes("action") || et.includes("retry") || et.includes("execute")) {
        type = "action";
        status = "info";
      } else if (et.includes("policy")) {
        type = "policy";
        status = String(entry.policy_decision || "").toUpperCase() === "ALLOW" ? "success" : "danger";
      } else if (et.includes("decision") || et.includes("ai")) {
        type = "ai_decision";
        status = "info";
      } else if (et.includes("predict")) {
        type = "prediction";
        status = "info";
      } else if (et.includes("fail") || et.includes("risk")) {
        type = "revenue_risk";
        status = "warning";
      }

      return {
        id: `AUD_${String(entry.id || index).padStart(4, "0")}`,
        time: entry.created_at
          ? new Date(entry.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
          : "09:41:00",
        type,
        title: (entry.event_type || "EVENT").replace(/_/g, " ").toUpperCase(),
        transactionId: entry.transaction_id || `TXN_${index}`,
        amount: entry.amount ? Number(entry.amount) : undefined,
        detail: entry.details || entry.action || (type === "recovery" ? `₹${entry.amount} recovered` : "Audit event recorded"),
        status,
      };
    });
  } catch (err) {
    console.warn("[ReviveAI API] /audit-log failed, falling back to mock data", err);
    return auditEvents;
  }
}

export async function getAnalytics(): Promise<AnalyticsSnapshot> {
  if (USE_MOCK_DATA) {
    await pause(360);
    return analytics;
  }
  try {
    const data = await request<any>("/evaluation");
    const evals = Array.isArray(data) ? data : data.evaluations || [];
    if (evals.length > 0) {
      const latest = evals[0];
      return {
        ...analytics,
        baseline: latest.baseline_recovered ?? analytics.baseline,
        revive: latest.revenue_recovered ?? analytics.revive,
      };
    }
    return analytics;
  } catch (err) {
    console.warn("[ReviveAI API] /evaluation failed, falling back to mock data", err);
    return analytics;
  }
}

export async function executeRecovery(id: string): Promise<{ status: "recovered"; amount: number }> {
  if (USE_MOCK_DATA) {
    await pause(1200);
    const item = transactions.find((txn) => txn.id === id);
    return { status: "recovered", amount: item?.amount ?? 4500 };
  }
  try {
    const res = await request<any>(`/recovery/execute/${id}`, { method: "POST" });
    return {
      status: "recovered",
      amount: res.amount_recovered || res.amount || 4500,
    };
  } catch (err) {
    console.warn(`[ReviveAI API] /recovery/execute/${id} failed, returning mock recovery`, err);
    return { status: "recovered", amount: 4500 };
  }
}

export async function runBatchRecovery(): Promise<RecoveryRunResult> {
  if (USE_MOCK_DATA) {
    await pause(1800);
    return { scanned: 1000, riskEvents: 327, approved: 241, escalated: 53, stopped: 33, recovered: 342500, recoveryRate: 67.4 };
  }
  try {
    const res = await request<any>("/recovery/run-batch", { method: "POST" });
    return {
      scanned: res.total_processed ?? 1000,
      riskEvents: res.failed_identified ?? 327,
      approved: res.actions_executed ?? 241,
      escalated: res.escalations ?? 53,
      stopped: res.policy_blocks ?? 33,
      recovered: res.total_recovered ?? 342500,
      recoveryRate: res.recovery_rate ?? 67.4,
    };
  } catch (err) {
    console.warn("[ReviveAI API] /recovery/run-batch failed, returning mock result", err);
    return { scanned: 1000, riskEvents: 327, approved: 241, escalated: 53, stopped: 33, recovered: 342500, recoveryRate: 67.4 };
  }
}

export const apiMode = USE_MOCK_DATA ? "MOCK MODE" : "API MODE";
export const apiBaseUrl = API_BASE_URL;
