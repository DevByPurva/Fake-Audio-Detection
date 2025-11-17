import os
from typing import Tuple

import joblib
import librosa
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


DATA_DIR = "audio_data"  # expected subfolders: audio_data/real, audio_data/fake
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "voice_detector_temp.pkl")
ALLOWED_EXTENSIONS = (".wav", ".wave")


def extract_features(file_path: str) -> np.ndarray:
    """Extract 12 MFCC + 3 spectral features, matching app.py expectations."""
    y, sr = librosa.load(file_path, sr=22050, duration=10)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc.T, axis=0)[:12]

    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
    zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))

    features = np.concatenate([
        mfcc_mean,
        [spectral_centroid / 1000.0],
        [spectral_rolloff / 1000.0],
        [zero_crossing_rate],
    ])
    return features


def load_dataset(data_dir: str = DATA_DIR) -> Tuple[np.ndarray, np.ndarray]:
    """Load WAV files from data_dir/real and data_dir/fake into X (features) and y (labels)."""
    X: list[np.ndarray] = []
    y: list[int] = []

    real_dir = os.path.join(data_dir, "real")
    fake_dir = os.path.join(data_dir, "fake")

    def add_dir(directory: str, label: int) -> None:
        if not os.path.isdir(directory):
            return
        for root, _, files in os.walk(directory):
            for name in files:
                if not name.lower().endswith(ALLOWED_EXTENSIONS):
                    continue
                path = os.path.join(root, name)
                try:
                    feats = extract_features(path)
                    X.append(feats)
                    y.append(label)
                except Exception as e:
                    print(f"[WARN] Skipping {path}: {e}")

    # 0 = Real, 1 = Fake (matches app.py logic)
    add_dir(real_dir, 0)
    add_dir(fake_dir, 1)

    if not X:
        raise RuntimeError(
            f"No audio files found under '{real_dir}' or '{fake_dir}'. "
            "Populate these folders with .wav files before training."
        )

    X_arr = np.vstack(X)
    y_arr = np.array(y, dtype=int)
    return X_arr, y_arr


def train_and_evaluate() -> None:
    print(f"Loading dataset from: {DATA_DIR}")
    X, y = load_dataset(DATA_DIR)
    print(f"Total samples: {len(y)}")
    print("Class distribution (0=Real, 1=Fake):",
          {cls: int((y == cls).sum()) for cls in np.unique(y)})

    stratify = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    print("Training RandomForestClassifier (voice detector)...")
    clf.fit(X_train, y_train)

    print("\nEvaluating on test set...")
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f}")

    print("\nClassification report:")
    print(classification_report(y_test, y_pred, digits=4))

    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, y_pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"\nSaved trained model to: {MODEL_PATH}")


if __name__ == "__main__":
    train_and_evaluate()
