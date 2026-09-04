import type { AnalyticsSnapshot, AuditEvent, DashboardMetrics, RecoveryDecision, Transaction } from "./types";

export const dashboardMetrics: DashboardMetrics = {
  revenueProcessed: 1840000,
  revenueAtRisk: 320000,
  revenueRecovered: 210000,
  recoveryRate: 65.6,
  automatedRecoveries: 241,
  humanEscalations: 53,
  processedDelta: 12.8,
  atRiskDelta: -4.6,
  recoveredDelta: 18.4,
  rateDelta: 7.2,
};

export const transactions: Transaction[] = [
  { id: "TXN_9281", amount: 4500, customer: "Customer 184", paymentMethod: "UPI", failureReason: "Bank Timeout", recoveryProbability: 91, aiAction: "retry", policy: "approved", status: "recovered", timestamp: "Today, 09:41:02", diagnosis: "Likely transient banking failure.", retryCount: 0, customerHistory: "8 previous successful payments" },
  { id: "TXN_9282", amount: 2100, customer: "Customer 291", paymentMethod: "Card", failureReason: "Insufficient Funds", recoveryProbability: 72, aiAction: "payment_link", policy: "approved", status: "pending", timestamp: "Today, 09:38:18", diagnosis: "Balance-related decline; payment link has the best recovery signal.", retryCount: 0, customerHistory: "3 previous successful payments" },
  { id: "TXN_9283", amount: 18000, customer: "Customer 832", paymentMethod: "UPI", failureReason: "Network Timeout", recoveryProbability: 84, aiAction: "retry", policy: "blocked", status: "human_review", timestamp: "Today, 09:36:44", diagnosis: "Retry is likely to succeed, but the amount exceeds the automated threshold.", retryCount: 0, customerHistory: "11 previous successful payments" },
  { id: "TXN_9284", amount: 7800, customer: "Customer 422", paymentMethod: "Netbanking", failureReason: "Issuer Unavailable", recoveryProbability: 79, aiAction: "retry", policy: "approved", status: "at_risk", timestamp: "Today, 09:32:11", diagnosis: "Issuer availability issue with a high transient-failure signature.", retryCount: 1, customerHistory: "5 previous successful payments" },
  { id: "TXN_9285", amount: 1250, customer: "Customer 104", paymentMethod: "Card", failureReason: "3DS Timeout", recoveryProbability: 88, aiAction: "retry", policy: "approved", status: "recovered", timestamp: "Today, 09:27:09", diagnosis: "Authentication window expired; a single retry is permitted.", retryCount: 0, customerHistory: "14 previous successful payments" },
  { id: "TXN_9286", amount: 28600, customer: "Customer 707", paymentMethod: "UPI", failureReason: "Daily Limit", recoveryProbability: 32, aiAction: "escalate", policy: "blocked", status: "blocked", timestamp: "Today, 09:24:55", diagnosis: "Failure is unlikely to resolve automatically within the current window.", retryCount: 0, customerHistory: "1 previous successful payment" },
  { id: "TXN_9287", amount: 5400, customer: "Customer 563", paymentMethod: "Wallet", failureReason: "Provider Timeout", recoveryProbability: 76, aiAction: "payment_link", policy: "pending", status: "pending", timestamp: "Today, 09:19:32", diagnosis: "Provider signal is mixed; payment link is safer than another automated retry.", retryCount: 0, customerHistory: "7 previous successful payments" },
  { id: "TXN_9288", amount: 9600, customer: "Customer 318", paymentMethod: "Netbanking", failureReason: "Bank Timeout", recoveryProbability: 82, aiAction: "retry", policy: "approved", status: "recovered", timestamp: "Today, 09:12:21", diagnosis: "Transient banking failure with high recent recovery rate.", retryCount: 0, customerHistory: "9 previous successful payments" },
];

export const decisions: RecoveryDecision[] = [
  { id: "DEC_0418", transactionId: "TXN_9281", amount: 4500, diagnosis: "Likely transient banking failure.", probability: 91, recommendation: "RETRY PAYMENT", confidence: 94, policy: "approved", outcome: "Recovered", reasons: ["Returning customer", "8 previous successful payments", "Failure is historically transient", "No previous recovery attempt"] },
  { id: "DEC_0417", transactionId: "TXN_9283", amount: 18000, diagnosis: "Retry may resolve the network timeout.", probability: 84, recommendation: "RETRY PAYMENT", confidence: 88, policy: "blocked", outcome: "Human review required", reasons: ["High recovery probability", "Amount exceeds automated threshold", "Manual approval required for high-value action"] },
  { id: "DEC_0416", transactionId: "TXN_9282", amount: 2100, diagnosis: "Balance-related decline.", probability: 72, recommendation: "CREATE PAYMENT LINK", confidence: 79, policy: "approved", outcome: "Pending", reasons: ["Customer has prior successful payments", "Payment link converts better for balance declines", "Within action threshold"] },
  { id: "DEC_0415", transactionId: "TXN_9285", amount: 1250, diagnosis: "3DS challenge timed out.", probability: 88, recommendation: "RETRY PAYMENT", confidence: 91, policy: "approved", outcome: "Recovered", reasons: ["Authentication timeout is transient", "Retry count available", "Low amount exposure"] },
];

export const auditEvents: AuditEvent[] = [
  { id: "AUD_0006", time: "09:41:08", type: "recovery", title: "RECOVERY", transactionId: "TXN_9281", amount: 4500, detail: "₹4,500 recovered", status: "success" },
  { id: "AUD_0005", time: "09:41:05", type: "action", title: "ACTION", transactionId: "TXN_9281", detail: "Retry executed", status: "info" },
  { id: "AUD_0004", time: "09:41:04", type: "policy", title: "POLICY", transactionId: "TXN_9281", detail: "Approved", status: "success" },
  { id: "AUD_0003", time: "09:41:04", type: "ai_decision", title: "AI DECISION", transactionId: "TXN_9281", detail: "Retry payment · 94% confidence", status: "info" },
  { id: "AUD_0002", time: "09:41:03", type: "prediction", title: "ML PREDICTION", transactionId: "TXN_9281", detail: "91% recovery probability", status: "info" },
  { id: "AUD_0001", time: "09:41:02", type: "revenue_risk", title: "REVENUE AT RISK", transactionId: "TXN_9281", amount: 4500, detail: "Bank timeout detected", status: "warning" },
  { id: "AUD_0000", time: "09:36:48", type: "policy", title: "POLICY", transactionId: "TXN_9283", amount: 18000, detail: "Blocked: amount exceeds automated threshold", status: "danger" },
];

export const analytics: AnalyticsSnapshot = {
  chart: [
    { label: "Aug 05", risk: 18000, recovered: 12400 }, { label: "Aug 10", risk: 24000, recovered: 16900 }, { label: "Aug 15", risk: 21000, recovered: 14800 }, { label: "Aug 20", risk: 29000, recovered: 20200 }, { label: "Aug 25", risk: 34000, recovered: 23400 }, { label: "Aug 30", risk: 31000, recovered: 21900 }, { label: "Sep 03", risk: 38000, recovered: 26700 },
  ],
  failureTypes: [
    { name: "Bank timeout", recovered: 82, total: 100 }, { name: "Network timeout", recovered: 74, total: 100 }, { name: "3DS timeout", recovered: 68, total: 100 }, { name: "Insufficient funds", recovered: 49, total: 100 },
  ],
  paymentMethods: [{ name: "UPI", value: 46, color: "#6DE7F2" }, { name: "Card", value: 31, color: "#8295FF" }, { name: "Netbanking", value: 15, color: "#B59BFF" }, { name: "Wallet", value: 8, color: "#F0B36B" }],
  segments: [{ name: "Returning", value: 78 }, { name: "New", value: 51 }, { name: "Enterprise", value: 86 }],
  probabilityDistribution: [{ bucket: "0–20", count: 12 }, { bucket: "21–40", count: 24 }, { bucket: "41–60", count: 48 }, { bucket: "61–80", count: 96 }, { bucket: "81–100", count: 143 }],
  baseline: 128000,
  revive: 210000,
};
