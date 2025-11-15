import os
from typing import Tuple

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


DATA_PATH = "BETTER30.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "better30_scam_text_model.pkl")


def load_better30_dataset(csv_path: str = DATA_PATH) -> pd.DataFrame:
    """Load BETTER30.csv and build a combined text field for classification."""
    df = pd.read_csv(csv_path)

    # Ensure required columns exist
    required_cols = ["TEXT", "LABEL"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in {csv_path}")

    # Use CONTEXT if available to enrich the text
    if "CONTEXT" in df.columns:
        df["CONTEXT"] = df["CONTEXT"].fillna("")
        df["combined_text"] = (
            df["TEXT"].astype(str).fillna("") + " " + df["CONTEXT"].astype(str)
        )
    else:
        df["combined_text"] = df["TEXT"].astype(str).fillna("")

    # Clean labels
    df["LABEL"] = df["LABEL"].astype(str).str.strip()

    # Drop rows with empty text or labels
    df = df[(df["combined_text"].str.len() > 0) & (df["LABEL"].str.len() > 0)]

    return df[["combined_text", "LABEL"]]


def train_test_split_better30(
    df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Split the dataset into train and test sets, handling rare labels safely."""
    X = df["combined_text"]
    y = df["LABEL"]

    # Stratify only if all labels have at least 2 samples
    label_counts = y.value_counts()
    rare_labels = label_counts[label_counts < 2].index.tolist()
    stratify = None if rare_labels else y

    if rare_labels:
        print(
            "Warning: the following labels have < 2 samples and will not be stratified:",
            rare_labels,
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    return X_train, X_test, y_train, y_test


def build_training_pipeline() -> Pipeline:
    """Create a TF-IDF + Logistic Regression pipeline for multi-class classification."""
    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=10000,
                    ngram_range=(1, 2),
                    stop_words="english",
                    min_df=2,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    n_jobs=-1,
                    multi_class="auto",
                    solver="lbfgs",
                ),
            ),
        ]
    )
    return pipeline


def train_and_evaluate() -> None:
    """Train the model on BETTER30.csv and print accuracy and detailed metrics."""
    print("Loading dataset from:", DATA_PATH)
    df = load_better30_dataset(DATA_PATH)
    print(f"Total samples: {len(df)}")
    print("Number of unique labels:", df["LABEL"].nunique())
    print("Labels:", sorted(df["LABEL"].unique()))

    X_train, X_test, y_train, y_test = train_test_split_better30(df)

    print("\nBuilding training pipeline (TF-IDF + Logistic Regression)...")
    pipeline = build_training_pipeline()

    print("Training model...")
    pipeline.fit(X_train, y_train)

    print("\nEvaluating on test set...")
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.4f}")

    print("\nClassification report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Confusion matrix with clear label ordering
    labels = sorted(df["LABEL"].unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)

    print("Confusion matrix (rows = true labels, columns = predicted labels):")
    try:
        import pandas as pd  # type: ignore[reimported]

        cm_df = pd.DataFrame(
            cm,
            index=[f"true_{lbl}" for lbl in labels],
            columns=[f"pred_{lbl}" for lbl in labels],
        )
        print(cm_df)
    except Exception:
        # Fallback to raw matrix
        print(cm)

    # Save the trained pipeline
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nSaved trained model to: {MODEL_PATH}")


if __name__ == "__main__":
    train_and_evaluate()
