#!/usr/bin/env python3
"""Import EventOps AI data from portable JSON into Google Cloud Firestore.

Usage:
    python scripts/import_eventops_data.py --project YOUR_PROJECT_ID [--input-dir DIR] [--dry-run] [--overwrite]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_eventops_data")


def validate_event_data(event: dict) -> bool:
    """Basic validation of required EventOps dossier fields."""
    required = ["event_id", "title", "total_budget", "status"]
    for r in required:
        if r not in event:
            logger.warning("Event missing required key: %s in record %s", r, event.get("event_id"))
            return False
    return True


def validate_decision_data(decision: dict) -> bool:
    """Basic validation of decision record fields."""
    required = ["decision_id", "event_id", "proposed_change", "approval_status"]
    for r in required:
        if r not in decision:
            logger.warning("Decision missing required key: %s in record %s", r, decision.get("decision_id"))
            return False
    return True


def import_firestore_data(
    project_id: str,
    input_dir: Path,
    dry_run: bool = False,
    overwrite: bool = False,
):
    events_path = input_dir / "events.json"
    decisions_path = input_dir / "decisions.json"
    manifest_path = input_dir / "export_manifest.json"

    if not events_path.exists():
        logger.error("Events file not found at %s", events_path)
        sys.exit(1)

    logger.info("Reading export files from %s", input_dir)
    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    decisions = []
    if decisions_path.exists():
        with open(decisions_path, "r", encoding="utf-8") as f:
            decisions = json.load(f)

    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    logger.info(
        "Manifest loaded: schema %s, %d events, %d decisions",
        manifest.get("schema_version", "unknown"),
        len(events),
        len(decisions),
    )

    # Validate before touching database
    logger.info("Validating %d events...", len(events))
    for evt in events:
        if not validate_event_data(evt):
            raise ValueError(f"Validation failed for event {evt.get('event_id')}")

    logger.info("Validating %d decisions...", len(decisions))
    for dec in decisions:
        if not validate_decision_data(dec):
            raise ValueError(f"Validation failed for decision {dec.get('decision_id')}")

    logger.info("Connecting to target Firestore project: %s", project_id)
    db = firestore.Client(project=project_id)

    # Check for existing events if overwrite is False
    existing_events = []
    for evt in events:
        doc_id = evt.get("event_id") or evt.get("_doc_id")
        doc_ref = db.collection("events").document(doc_id)
        if doc_ref.get().exists:
            existing_events.append(doc_id)

    if existing_events and not overwrite and not dry_run:
        logger.error(
            "Found %d existing events in target database: %s. Refusing to overwrite without --overwrite flag.",
            len(existing_events),
            existing_events,
        )
        sys.exit(1)

    if dry_run:
        logger.info("[DRY-RUN] Pre-import verification successful:")
        logger.info("  Target project: %s", project_id)
        logger.info("  Events to write: %d", len(events))
        logger.info("  Decisions to write: %d", len(decisions))
        logger.info("  Existing conflicts: %d", len(existing_events))
        logger.info("  Overwrite flag: %s", overwrite)
        return

    # Write events
    for evt in events:
        doc_id = evt.get("event_id") or evt.get("_doc_id")
        clean_evt = {k: v for k, v in evt.items() if not k.startswith("_")}
        db.collection("events").document(doc_id).set(clean_evt)
        logger.info("Restored event: %s (%s)", doc_id, clean_evt.get("title"))

    # Write decisions subcollection
    for dec in decisions:
        event_id = dec["event_id"]
        decision_id = dec.get("decision_id") or dec.get("_doc_id")
        clean_dec = {k: v for k, v in dec.items() if not k.startswith("_")}
        (
            db.collection("events")
            .document(event_id)
            .collection("decisions")
            .document(decision_id)
            .set(clean_dec)
        )
        logger.info("Restored decision: %s for event: %s", decision_id, event_id)

    logger.info("Data restoration completed successfully into project: %s", project_id)


def main():
    parser = argparse.ArgumentParser(description="Import EventOps AI Firestore data from portable JSON")
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="Target GCP Project ID (or set GOOGLE_CLOUD_PROJECT env var)",
    )
    parser.add_argument(
        "--input-dir",
        default="backups/firestore",
        help="Input directory with exported JSON files (default: backups/firestore)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate JSON data and check target database without writing changes",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing documents in the target database",
    )

    args = parser.parse_args()
    if not args.project:
        logger.error("Project ID is required. Pass --project <PROJECT_ID> or set GOOGLE_CLOUD_PROJECT.")
        sys.exit(1)

    input_dir = Path(args.input_dir)
    import_firestore_data(args.project, input_dir, args.dry_run, args.overwrite)


if __name__ == "__main__":
    main()
