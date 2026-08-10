"""
Dataset versioning pipeline — the "MERGE_STAGING" + "PROFILE" steps of the
MLOps human-in-the-loop flywheel.

Flow: a supervisor corrects YOLO's boxes on a detection (see
camera_management.views.review_detection), which creates an approved
StagedCorrection. Once enough of those pile up, this module validates them
(image readable, labels valid, coordinates in bounds, not a duplicate),
folds them into yolo/data/dataset_finale/{train,val,test}/ in YOLO label
format, and snapshots a per-version class-distribution profile.

Mirrors the same shape as a cloud-hosted version of this pipeline (staging
bucket -> validate -> merge into a cumulative dataset -> profile), just
running against the local filesystem/database instead of S3 + a managed
cron — cheap enough to run entirely inside this app's own containers.

Class balancing and augmentation are intentionally NOT reimplemented here:
Ultralytics' own model.train() already applies mosaic/flip/HSV augmentation
by default, so a second custom augmentation pass would just be redundant.
"""
import csv
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from django.conf import settings
from PIL import Image

log = logging.getLogger(__name__)

LABEL_TO_INDEX = {'fire': 0, 'other': 1, 'smoke': 2}

DATASET_ROOT = Path(settings.BASE_DIR) / 'yolo' / 'data' / 'dataset_finale'
PROFILES_ROOT = Path(settings.BASE_DIR) / 'yolo' / 'data' / 'profiles'
REGISTRY_ROOT = DATASET_ROOT / '_registry'

MIN_BATCH_SIZE = int(os.environ.get('MLOPS_MIN_STAGING_BATCH', 50))


def _now():
    return datetime.now(timezone.utc)


def _image_hash(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _validate_correction(correction):
    """Returns (is_valid, reason)."""
    detection = correction.detection
    if detection is None or not detection.image or not os.path.exists(detection.image.path):
        return False, 'source image missing on disk'

    try:
        with Image.open(detection.image.path) as im:
            width, height = im.size
    except Exception as exc:
        return False, f'unreadable image: {exc}'

    for box in correction.boxes:
        if box.get('label') not in LABEL_TO_INDEX:
            return False, f"invalid label '{box.get('label')}'"
        x1, y1, x2, y2 = box['x1'], box['y1'], box['x2'], box['y2']
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            return False, 'box coordinates out of image bounds'

    return True, ''


def _assign_split(counters):
    """Deterministic ~80/10/10 split using a running counter."""
    n = counters.get('total_assigned', 0)
    counters['total_assigned'] = n + 1
    if n % 10 == 8:
        return 'val'
    if n % 10 == 9:
        return 'test'
    return 'train'


def run_merge_staging(min_batch_size=None):
    """
    Validates + merges all pending StagedCorrection rows into
    yolo/data/dataset_finale/. No-ops if there aren't at least
    `min_batch_size` of them yet (MLOPS_MIN_STAGING_BATCH env var,
    default 50 — a real deployment collecting from many cameras would
    set this much higher, e.g. 500+).

    Returns the new dataset version string, or None if nothing was merged.
    """
    from camera_management.models import StagedCorrection, DatasetVersion

    threshold = min_batch_size if min_batch_size is not None else MIN_BATCH_SIZE
    pending = list(StagedCorrection.objects.filter(status='approved').select_related('detection'))

    if len(pending) < threshold:
        log.info("merge_staging: only %d pending correction(s), need %d — skipping.", len(pending), threshold)
        return None

    for split in ('train', 'val', 'test'):
        (DATASET_ROOT / split / 'images').mkdir(parents=True, exist_ok=True)
        (DATASET_ROOT / split / 'labels').mkdir(parents=True, exist_ok=True)
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    PROFILES_ROOT.mkdir(parents=True, exist_ok=True)

    counters = _load_json(REGISTRY_ROOT / 'counters.json', {})
    seen_hashes = set(_load_json(REGISTRY_ROOT / 'seen_hashes.json', []))

    version = _now().strftime('%Y%m%d-%H%M%S')
    registry_rows = []
    merged, rejected = [], []

    for correction in pending:
        is_valid, reason = _validate_correction(correction)
        if not is_valid:
            correction.status = 'rejected'
            correction.reject_reason = reason
            rejected.append(correction)
            continue

        image_path = correction.detection.image.path
        image_hash = _image_hash(image_path)
        if image_hash in seen_hashes:
            correction.status = 'rejected'
            correction.reject_reason = 'duplicate image already in dataset_finale'
            rejected.append(correction)
            continue

        split = _assign_split(counters)
        stem = f'img_{correction.detection_id}_{image_hash[:8]}'
        dest_image = DATASET_ROOT / split / 'images' / f'{stem}{Path(image_path).suffix or ".jpg"}'
        dest_label = DATASET_ROOT / split / 'labels' / f'{stem}.txt'

        with Image.open(image_path) as im:
            width, height = im.size
            im.convert('RGB').save(dest_image)

        label_lines = []
        for box in correction.boxes:
            cx = ((box['x1'] + box['x2']) / 2) / width
            cy = ((box['y1'] + box['y2']) / 2) / height
            w = (box['x2'] - box['x1']) / width
            h = (box['y2'] - box['y1']) / height
            label_lines.append(f"{LABEL_TO_INDEX[box['label']]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        dest_label.write_text('\n'.join(label_lines))

        seen_hashes.add(image_hash)
        registry_rows.append({
            'image': dest_image.name, 'split': split,
            'source_detection_id': correction.detection_id,
            'num_boxes': len(correction.boxes), 'merged_at': _now().isoformat(),
        })
        correction.status = 'merged'
        correction.merged_at = _now()
        merged.append(correction)

    if merged or rejected:
        StagedCorrection.objects.bulk_update(merged + rejected, ['status', 'reject_reason', 'merged_at'])

    if not merged:
        log.info("merge_staging: batch had %d correction(s), none valid — nothing merged.", len(pending))
        return None

    (REGISTRY_ROOT / 'counters.json').write_text(json.dumps(counters, indent=2))
    (REGISTRY_ROOT / 'seen_hashes.json').write_text(json.dumps(sorted(seen_hashes)))

    registry_csv = REGISTRY_ROOT / f'{version}.csv'
    with open(registry_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['image', 'split', 'source_detection_id', 'num_boxes', 'merged_at'])
        writer.writeheader()
        writer.writerows(registry_rows)

    # ── PROFILE step: snapshot the whole dataset_finale's class distribution ──
    class_counts = {label: 0 for label in LABEL_TO_INDEX}
    split_counts = {'train': 0, 'val': 0, 'test': 0}
    for split in split_counts:
        label_files = list((DATASET_ROOT / split / 'labels').glob('*.txt'))
        split_counts[split] = len(label_files)
        for lf in label_files:
            for line in lf.read_text().splitlines():
                if not line.strip():
                    continue
                idx = int(line.split()[0])
                for label, i in LABEL_TO_INDEX.items():
                    if i == idx:
                        class_counts[label] += 1

    total_images = sum(split_counts.values())
    profile = {
        'version': version, 'total_images': total_images,
        'splits': split_counts, 'class_counts': class_counts,
        'newly_merged': len(merged), 'newly_rejected': len(rejected),
    }
    version_dir = PROFILES_ROOT / version
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / 'dataset_profile.json').write_text(json.dumps(profile, indent=2))

    versions_history = _load_json(PROFILES_ROOT / 'versions.json', [])
    versions_history.append({'version': version, 'total_images': total_images, 'created_at': _now().isoformat()})
    (PROFILES_ROOT / 'versions.json').write_text(json.dumps(versions_history, indent=2))

    DatasetVersion.objects.create(
        version=version, image_count=total_images,
        train_count=split_counts['train'], val_count=split_counts['val'], test_count=split_counts['test'],
        class_counts=class_counts,
    )

    log.info(
        "merge_staging: version %s — merged %d, rejected %d. Dataset now has %d images (%s).",
        version, len(merged), len(rejected), total_images, split_counts,
    )
    return version


@shared_task(name="merge_staging_task")
def merge_staging_task():
    run_merge_staging()
