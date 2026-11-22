"""Keras triage classifier (docs/spec/05). Two views of the same text, joined:
  words       TextVectorization (unigrams + bigrams) -> Embedding(64) -> GlobalAveragePooling
  characters  TextVectorization (character 3- and 4-grams) -> Embedding(64) -> GlobalAveragePooling
              (a typo changes one word completely, but only a few character n-grams: it survives typos)
  -> Dense(32, relu) -> Dense(3, softmax). Class weights make a missed emergency cost more.

Training data (team decision 21 Nov 2026): data/voice/triage_phrases.csv (all splits) + data/voice/external_phrases.csv,
plus augmentation (voice/triage/augment.py: typos, fillers, paraphrases, long mixed messages).
15 % of the ORIGINAL phrases (stratified, seed 2026) are kept apart, without augmentation, to choose the epoch.
data/voice/holdout_phrases.csv is NEVER used here: it is only for the evaluation (voice/eval/evaluate.py).

Retrain:  docker compose run --rm voice python -m voice.triage.classifier
The model is saved to voice/models/triage_classifier.keras (git-ignored).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from voice.triage.augment import augment
from voice.triage.text import normalize

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "voice" / "models" / "triage_classifier.keras"
DATA = [ROOT / "data" / "voice" / "triage_phrases.csv", ROOT / "data" / "voice" / "external_phrases.csv"]
LABELS = ["routine", "urgent", "emergency"]
CLASS_WEIGHT = {0: 1.0, 1: 1.5, 2: 3.0}        # ASSUMPTION: missing an emergency costs 3x a routine error
SEED = 2026


def training_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train with augmentation, validation of untouched originals)."""
    df = pd.concat([pd.read_csv(f)[["text", "label"]] for f in DATA], ignore_index=True).drop_duplicates("text")
    val = df.groupby("label", group_keys=False).sample(frac=0.15, random_state=SEED)
    train = augment(df.drop(val.index), seed=SEED)
    return train, val


def build_and_train(epochs: int = 40) -> "tf.keras.Model":  # noqa: F821
    import tensorflow as tf
    tf.keras.utils.set_random_seed(SEED)
    train, val = training_data()
    as_text = lambda col: tf.constant([normalize(t) for t in col], shape=(len(col), 1))  # noqa: E731 - string tensors
    x_train, x_val = as_text(train.text), as_text(val.text)
    y_train, y_val = train.label.map(LABELS.index).to_numpy(), val.label.map(LABELS.index).to_numpy()

    words = tf.keras.layers.TextVectorization(max_tokens=12000, ngrams=2, output_sequence_length=96)
    chars = tf.keras.layers.TextVectorization(max_tokens=20000, split="character", ngrams=(3, 4),
                                              output_sequence_length=600)
    words.adapt(x_train)
    chars.adapt(x_train)
    inputs = tf.keras.Input(shape=(1,), dtype=tf.string)
    w = tf.keras.layers.GlobalAveragePooling1D()(tf.keras.layers.Embedding(12000 + 1, 64, mask_zero=True)(words(inputs)))
    c = tf.keras.layers.GlobalAveragePooling1D()(tf.keras.layers.Embedding(20000 + 1, 64, mask_zero=True)(chars(inputs)))
    x = tf.keras.layers.Concatenate()([w, c])
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(3, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(0.003), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(x_train, y_train, validation_data=(x_val, y_val), epochs=epochs, batch_size=64, class_weight=CLASS_WEIGHT,
              verbose=0, callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True)])
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(MODEL_PATH)
    return model


def load() -> "tf.keras.Model":  # noqa: F821
    import tensorflow as tf
    return tf.keras.models.load_model(MODEL_PATH)


def predict(model, texts: list[str]) -> list[dict]:
    import tensorflow as tf
    probs = model.predict(tf.constant([normalize(t) for t in texts], shape=(len(texts), 1)), verbose=0)
    return [{"label": LABELS[int(np.argmax(p))], "probs": {l: round(float(v), 4) for l, v in zip(LABELS, p)}} for p in probs]


if __name__ == "__main__":
    m = build_and_train()
    train, val = training_data()
    pred = [p["label"] for p in predict(m, val.text.tolist())]
    print(f"saved {MODEL_PATH}  ·  train {len(train)} rows (augmented)  ·  validation {len(val)} originals, "
          f"accuracy {np.mean(np.array(pred) == val.label.to_numpy()):.3f}")
    print("seed", SEED, "· tensorflow", __import__("tensorflow").__version__, "· pid", os.getpid())
