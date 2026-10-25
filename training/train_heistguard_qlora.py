"""Train the deployed CPU classifier and record measured held-out metrics.

Historical filename retained for callers; this trains TF-IDF logistic regression,
not QLoRA or a Llama adapter.
"""
from __future__ import annotations
import hashlib
import json
import pickle
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from kernel.live_agent_parser import normalize_and_decode_obfuscations
TRAIN_JSONL_DATA = PROJECT_ROOT / 'training/data/heistguard_train.jsonl'
MODEL_WEIGHTS_PATH = PROJECT_ROOT / 'training/models/heistguard_lora_weights.pkl'
EVIDENCE_PATH = PROJECT_ROOT / 'shared/qlora_evidence.json'


def metrics(labels, predictions):
    p, r, f1, _ = precision_recall_fscore_support(labels, predictions, average='binary', zero_division=0)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {'accuracy': float(accuracy_score(labels, predictions)), 'precision': float(p),
            'recall': float(r), 'f1_score': float(f1), 'false_positive_rate': float(fp / max(1, tn + fp)),
            'confusion_matrix': {'true_negative': int(tn), 'false_positive': int(fp),
                                 'false_negative': int(fn), 'true_positive': int(tp)}}


def generate_and_save_qlora_evidence():
    raw = TRAIN_JSONL_DATA.read_bytes()
    unique, conflicts = {}, set()
    for line in raw.decode('utf-8').splitlines():
        row = json.loads(line)
        text = normalize_and_decode_obfuscations(row.get('prompt_text') or row.get('text') or '').strip()
        if not text:
            continue
        value = row.get('label', row.get('is_malicious'))
        if value not in (0, 1, '0', '1', 'DECEPTIVE_INJECTION', 'BENIGN_ENTITLEMENT'):
            raise ValueError(f'Unrecognized training label: {value!r}')
        label = int(value in (1, '1', 'DECEPTIVE_INJECTION'))
        key = ' '.join(text.casefold().split())
        if key in unique and unique[key][1] != label:
            conflicts.add(key)
        unique.setdefault(key, (text, label, row.get('source_dataset', row.get('source', 'local'))))
    records = [r for k, r in unique.items() if k not in conflicts]
    train, val = train_test_split(records, test_size=0.2, random_state=42, stratify=[r[1] for r in records])
    train_texts, train_labels = [r[0] for r in train], [r[1] for r in train]
    val_texts, val_labels = [r[0] for r in val], [r[1] for r in val]
    pipeline = Pipeline([
        ('features', FeatureUnion([
            ('word', TfidfVectorizer(ngram_range=(1, 3), max_features=20000, sublinear_tf=True)),
            ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=30000, sublinear_tf=True)),
        ])),
        ('clf', LogisticRegression(C=4.0, max_iter=700, class_weight='balanced', random_state=42)),
    ])
    baseline = None
    if MODEL_WEIGHTS_PATH.exists():
        try:
            with MODEL_WEIGHTS_PATH.open('rb') as f:
                previous = pickle.load(f)
            baseline = metrics(val_labels, previous.predict(val_texts))
        except (ValueError, OSError, pickle.UnpicklingError):
            pass
    started = time.perf_counter()
    pipeline.fit(train_texts, train_labels)
    duration = time.perf_counter() - started
    predictions = pipeline.predict(val_texts)
    scores = metrics(val_labels, predictions)
    if baseline and scores['f1_score'] < baseline['f1_score']:
        raise RuntimeError(f'Candidate F1 {scores["f1_score"]:.4f} below previous {baseline["f1_score"]:.4f}; deployment skipped')
    MODEL_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MODEL_WEIGHTS_PATH.with_suffix('.pkl.tmp')
    with temporary.open('wb') as f:
        pickle.dump(pipeline, f)
    temporary.replace(MODEL_WEIGHTS_PATH)
    latencies = []
    for text in val_texts[:50]:
        tick = time.perf_counter()
        pipeline.predict_proba([text])
        latencies.append((time.perf_counter() - tick) * 1000)
    latencies.sort()
    scores.update(p50_latency_ms=latencies[len(latencies)//2], p95_latency_ms=latencies[int(len(latencies)*0.95)])
    digest = hashlib.sha256(MODEL_WEIGHTS_PATH.read_bytes()).hexdigest()
    evidence = {
        'engine': 'HeistGuard TF-IDF word/character logistic regression',
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'hardware': {'training_device': 'cpu', 'gpu_name': None},
        'verification': 'MEASURED_HELD_OUT_EVALUATION',
        'checkpoint_sha256': digest, 'checkpoint_path': str(MODEL_WEIGHTS_PATH),
        'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'dataset_rows': len(records),
        'training_rows': len(train), 'validation_rows': len(val), 'conflicting_texts_removed': len(conflicts),
        'split': '80/20 stratified, seed 42, normalized text deduplicated before split',
        'baseline_caveat': 'Previous model may have seen older domain examples; comparison uses the same refreshed holdout.',
        'training_time_sec': round(duration, 3), 'metrics': scores, 'previous_model_metrics': baseline,
        'provenance_breakdown': dict(Counter(r[2] for r in records)),
        'validation_by_source': {source: metrics([r[1] for r in val if r[2] == source],
            [int(predictions[i]) for i, r in enumerate(val) if r[2] == source]) for source in sorted({r[2] for r in val})},
        'training_run': {'weights_path': str(MODEL_WEIGHTS_PATH), 'weights_sha256': digest,
                         'weights_size_bytes': MODEL_WEIGHTS_PATH.stat().st_size},
        'sample_predictions': [{'prompt': text[:120], 'true_label': label,
            'predicted_deception_prob': float(pipeline.predict_proba([text])[0][1])}
            for text, label, _ in val[:5]],
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = EVIDENCE_PATH.with_suffix('.json.tmp')
    temp.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    temp.replace(EVIDENCE_PATH)
    return evidence


if __name__ == '__main__':
    result = generate_and_save_qlora_evidence()
    print(json.dumps({k: result[k] for k in ('dataset_rows', 'training_rows', 'validation_rows', 'metrics', 'previous_model_metrics')}, indent=2))
