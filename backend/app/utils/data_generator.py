"""
Synthetic transaction data generator for ReviveAI.

Generates statistically realistic payment transactions with
correlated features and outcomes.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import numpy as np

SEED = 42

PAYMENT_METHODS = ["upi", "credit_card", "debit_card", "net_banking", "wallet"]
PAYMENT_METHOD_WEIGHTS = [0.35, 0.25, 0.20, 0.12, 0.08]

FAILURE_CATEGORIES = [
    "temporary_bank_failure",
    "insufficient_funds",
    "authentication_failure",
    "network_timeout",
    "expired_card",
    "risk_decline",
    "invalid_details",
    "unknown",
]
FAILURE_WEIGHTS = [0.25, 0.20, 0.15, 0.15, 0.08, 0.07, 0.05, 0.05]

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
DEVICE_WEIGHTS = [0.60, 0.30, 0.10]

LOCATIONS = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
    "Chandigarh", "Kochi", "Indore", "Nagpur", "Bhopal",
]

MERCHANT_CATEGORIES = [
    "ecommerce", "food_delivery", "travel", "utilities",
    "subscription", "education", "healthcare", "entertainment",
]

# Base recovery probability per failure type
FAILURE_RECOVERY_BASE = {
    "temporary_bank_failure": 0.78,
    "insufficient_funds": 0.35,
    "authentication_failure": 0.52,
    "network_timeout": 0.82,
    "expired_card": 0.18,
    "risk_decline": 0.12,
    "invalid_details": 0.08,
    "unknown": 0.25,
}

FAILURE_REASONS = {
    "temporary_bank_failure": [
        "Bank server temporarily unavailable",
        "Transaction processing timeout at bank",
        "Bank system under maintenance",
        "Temporary connectivity issue with bank",
    ],
    "insufficient_funds": [
        "Account balance insufficient for transaction",
        "Available balance less than transaction amount",
        "Daily transaction limit exceeded",
    ],
    "authentication_failure": [
        "OTP verification failed",
        "3D Secure authentication failed",
        "PIN verification unsuccessful",
        "Biometric authentication failed",
    ],
    "network_timeout": [
        "Connection timed out during processing",
        "Network interruption during payment",
        "Gateway timeout - no response from bank",
    ],
    "expired_card": [
        "Card has expired",
        "Card validity period ended",
    ],
    "risk_decline": [
        "Transaction flagged by risk engine",
        "Suspicious transaction pattern detected",
        "Geographic anomaly detected",
    ],
    "invalid_details": [
        "Invalid card number",
        "Invalid CVV",
        "Account number mismatch",
    ],
    "unknown": [
        "Unexpected processing error",
        "Unclassified payment failure",
    ],
}


def generate_customers(n_customers: int, rng: np.random.Generator) -> List[Dict]:
    """Generate synthetic customer profiles."""
    customers = []
    for i in range(n_customers):
        customer_id = f"CUST_{i+1:05d}"
        prev_txns = int(rng.exponential(scale=8)) + 1
        success_rate = float(np.clip(rng.beta(8, 2), 0.3, 1.0))
        prev_failures = max(0, int(prev_txns * (1 - success_rate)))
        ltv = float(rng.lognormal(mean=8, sigma=1.2))
        days_since = int(rng.exponential(scale=30)) + 1
        last_txn_time = datetime.now() - timedelta(days=days_since)

        customers.append({
            "customer_id": customer_id,
            "previous_transactions": prev_txns,
            "success_rate": round(success_rate, 4),
            "previous_failures": prev_failures,
            "lifetime_value": round(ltv, 2),
            "last_transaction_time": last_txn_time,
        })
    return customers


def _compute_recovery_probability(
    failure_code: str,
    customer: Dict,
    amount: float,
    retry_count: int,
    payment_method: str,
    is_returning: bool,
    rng: np.random.Generator,
) -> float:
    """Compute recovery probability with realistic correlations."""
    base = FAILURE_RECOVERY_BASE.get(failure_code, 0.25)

    # Returning customer boost
    if is_returning:
        base += 0.08

    # High success rate customer boost
    if customer["success_rate"] > 0.85:
        base += 0.10
    elif customer["success_rate"] > 0.70:
        base += 0.05

    # More previous transactions = more reliable
    if customer["previous_transactions"] > 10:
        base += 0.05

    # High amount penalty
    if amount > 50000:
        base -= 0.15
    elif amount > 20000:
        base -= 0.08
    elif amount > 10000:
        base -= 0.04

    # Retry penalty
    base -= retry_count * 0.20

    # Payment method factor
    if payment_method == "upi":
        base += 0.04
    elif payment_method == "wallet":
        base += 0.03
    elif payment_method == "net_banking":
        base -= 0.03

    # High LTV boost
    if customer["lifetime_value"] > 50000:
        base += 0.05

    # Add noise
    noise = float(rng.normal(0, 0.05))
    prob = np.clip(base + noise, 0.02, 0.98)
    return round(float(prob), 4)


def _decide_outcome(recovery_prob: float, rng: np.random.Generator) -> str:
    """Determine if recovery would succeed based on probability."""
    return "recovered" if rng.random() < recovery_prob else "failed"


def generate_transactions(
    n_transactions: int = 10000,
    failure_rate: float = 0.32,
    seed: int = SEED,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate synthetic transaction data with realistic correlations.

    Returns:
        (transactions, customers)
    """
    rng = np.random.default_rng(seed)
    py_random = random.Random(seed)

    # Generate customers
    n_customers = max(500, n_transactions // 8)
    customers = generate_customers(n_customers, rng)
    customer_lookup = {c["customer_id"]: c for c in customers}

    transactions = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(n_transactions):
        txn_id = f"TXN_{i+1:06d}"
        customer = py_random.choice(customers)
        is_failed = rng.random() < failure_rate

        # Amount: lognormal distribution (INR)
        amount = float(np.clip(rng.lognormal(mean=7.5, sigma=1.0), 50, 200000))
        amount = round(amount, 2)

        payment_method = py_random.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS, k=1)[0]
        device = py_random.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS, k=1)[0]
        location = py_random.choice(LOCATIONS)
        category = py_random.choice(MERCHANT_CATEGORIES)
        is_returning = customer["previous_transactions"] > 3

        # Checkout duration (seconds)
        checkout_dur = float(np.clip(rng.lognormal(mean=4.5, sigma=0.5), 30, 600))
        txn_freq = float(np.clip(rng.exponential(3), 0.1, 20))

        # Timestamps spread across 30 days
        time_offset = timedelta(
            seconds=int(rng.uniform(0, 30 * 24 * 3600))
        )
        timestamp = base_time + time_offset

        if is_failed:
            failure_code = py_random.choices(FAILURE_CATEGORIES, weights=FAILURE_WEIGHTS, k=1)[0]
            failure_reason = py_random.choice(FAILURE_REASONS[failure_code])

            # Some failures already have retries
            if failure_code in ("temporary_bank_failure", "network_timeout"):
                retry_count = py_random.choices([0, 1, 2], weights=[0.6, 0.3, 0.1], k=1)[0]
            else:
                retry_count = py_random.choices([0, 1], weights=[0.85, 0.15], k=1)[0]

            recovery_prob = _compute_recovery_probability(
                failure_code, customer, amount, retry_count,
                payment_method, is_returning, rng
            )
            final_outcome = _decide_outcome(recovery_prob, rng)
            payment_status = "failed"
        else:
            failure_code = None
            failure_reason = None
            retry_count = 0
            recovery_prob = None
            final_outcome = "success"
            payment_status = "success"

        transactions.append({
            "transaction_id": txn_id,
            "customer_id": customer["customer_id"],
            "merchant_id": "MERCHANT_001",
            "amount": amount,
            "currency": "INR",
            "payment_method": payment_method,
            "payment_status": payment_status,
            "failure_code": failure_code,
            "failure_reason": failure_reason,
            "retry_count": retry_count,
            "device_type": device,
            "location": location,
            "merchant_category": category,
            "checkout_duration": round(checkout_dur, 1),
            "cart_value": round(amount * float(rng.uniform(0.8, 1.2)), 2),
            "is_returning_customer": is_returning,
            "transaction_frequency": round(txn_freq, 2),
            "created_at": timestamp,
            # ML target fields (used for training, NOT exposed to model as features)
            "_recovery_probability": recovery_prob,
            "_final_outcome": final_outcome,
        })

    return transactions, customers


def get_ml_dataset(transactions: List[Dict]) -> Tuple[List[Dict], List[int]]:
    """
    Extract ML features and labels from failed transactions.

    Returns:
        (feature_dicts, labels)  where label=1 means recoverable
    """
    features = []
    labels = []

    for txn in transactions:
        if txn["payment_status"] != "failed":
            continue

        features.append({
            "amount": txn["amount"],
            "payment_method": txn["payment_method"],
            "failure_code": txn["failure_code"],
            "retry_count": txn["retry_count"],
            "device_type": txn["device_type"],
            "checkout_duration": txn["checkout_duration"],
            "cart_value": txn["cart_value"],
            "is_returning_customer": int(txn["is_returning_customer"]),
            "transaction_frequency": txn["transaction_frequency"],
            "merchant_category": txn["merchant_category"],
        })
        labels.append(1 if txn["_final_outcome"] == "recovered" else 0)

    return features, labels
