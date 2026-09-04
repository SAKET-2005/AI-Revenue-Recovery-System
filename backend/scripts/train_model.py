"""
Train the ML recovery prediction model.

Run: python -m scripts.train_model
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.data_generator import generate_transactions, get_ml_dataset
from app.ml.trainer import RecoveryModelTrainer


def main():
    print("=" * 60)
    print("  ReviveAI — ML Model Training")
    print("=" * 60)

    # Generate training data
    print("\n[1/4] Generating synthetic data...")
    transactions, customers = generate_transactions(n_transactions=10000, seed=42)
    print(f"  Total transactions: {len(transactions)}")
    failed = [t for t in transactions if t['payment_status'] == 'failed']
    print(f"  Failed transactions: {len(failed)}")

    # Extract ML dataset
    print("\n[2/4] Preparing ML features...")
    features, labels = get_ml_dataset(transactions)
    print(f"  Feature vectors: {len(features)}")
    print(f"  Positive (recoverable): {sum(labels)}")
    print(f"  Negative (not recoverable): {len(labels) - sum(labels)}")
    print(f"  Recovery rate: {sum(labels)/len(labels):.1%}")

    # Train model
    print("\n[3/4] Training XGBoost model...")
    trainer = RecoveryModelTrainer(seed=42)
    metrics = trainer.train(features, labels)

    print("\n  --- Model Metrics ---")
    print(f"  ROC-AUC:    {metrics['roc_auc']:.4f}")
    print(f"  Precision:  {metrics['precision']:.4f}")
    print(f"  Recall:     {metrics['recall']:.4f}")
    print(f"  F1 Score:   {metrics['f1']:.4f}")
    print(f"  Accuracy:   {metrics['accuracy']:.4f}")
    print(f"  Train size: {metrics['train_size']}")
    print(f"  Test size:  {metrics['test_size']}")

    print("\n  Confusion Matrix:")
    cm = metrics['confusion_matrix']
    print(f"    TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"    FN={cm[1][0]}  TP={cm[1][1]}")

    print("\n  Feature Importances:")
    sorted_fi = sorted(metrics['feature_importances'].items(), key=lambda x: x[1], reverse=True)
    for name, imp in sorted_fi:
        bar = "#" * int(imp * 50)
        print(f"    {name:<25} {imp:.4f} {bar}")

    # Save
    print("\n[4/4] Saving model artifacts...")
    trainer.save()
    print(f"  Saved to: {os.path.abspath(trainer.__class__.__dict__.get('_save_path', 'ml_artifacts/'))}")
    print("  [OK] recovery_model.joblib")
    print("  [OK] label_encoders.joblib")
    print("  [OK] feature_names.joblib")
    print("  [OK] metrics.json")

    print("\n" + "=" * 60)
    print("  Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
