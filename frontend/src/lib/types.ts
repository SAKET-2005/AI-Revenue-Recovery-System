export type TransactionStatus = "recovered" | "pending" | "human_review" | "blocked" | "at_risk";
export type PolicyStatus = "approved" | "pending" | "blocked";
export type RecoveryAction = "retry" | "payment_link" | "escalate" | "none";
export type EventType = "revenue_risk" | "prediction" | "ai_decision" | "policy" | "action" | "recovery";

export type PaymentMethod = "UPI" | "Card" | "Netbanking" | "Wallet";

export interface Transaction {
  id: string;
  amount: number;
  customer: string;
  paymentMethod: PaymentMethod;
  failureReason: string;
  recoveryProbability: number;
  aiAction: RecoveryAction;
  policy: PolicyStatus;
  status: TransactionStatus;
  timestamp: string;
  diagnosis: string;
  retryCount: number;
  customerHistory: string;
}

export interface DashboardMetrics {
  revenueProcessed: number;
  revenueAtRisk: number;
  revenueRecovered: number;
  recoveryRate: number;
  automatedRecoveries: number;
  humanEscalations: number;
  processedDelta: number;
  atRiskDelta: number;
  recoveredDelta: number;
  rateDelta: number;
}

export interface RecoveryDecision {
  id: string;
  transactionId: string;
  amount: number;
  diagnosis: string;
  probability: number;
  recommendation: string;
  confidence: number;
  policy: PolicyStatus;
  outcome: string;
  reasons: string[];
}

export interface AuditEvent {
  id: string;
  time: string;
  type: EventType;
  title: string;
  transactionId: string;
  amount?: number;
  detail: string;
  status: "success" | "info" | "warning" | "danger";
}

export interface RecoveryRunResult {
  scanned: number;
  riskEvents: number;
  approved: number;
  escalated: number;
  stopped: number;
  recovered: number;
  recoveryRate: number;
}

export interface ChartPoint {
  label: string;
  risk: number;
  recovered: number;
}

export interface AnalyticsSnapshot {
  chart: ChartPoint[];
  failureTypes: { name: string; recovered: number; total: number }[];
  paymentMethods: { name: string; value: number; color: string }[];
  segments: { name: string; value: number }[];
  probabilityDistribution: { bucket: string; count: number }[];
  baseline: number;
  revive: number;
}
