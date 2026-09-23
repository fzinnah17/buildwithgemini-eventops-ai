#!/usr/bin/env python3
"""Export EventOps AI data from Google Cloud Firestore to portable JSON.

Usage:
    python scripts/export_eventops_data.py [--dry-run] [--output-dir DIR] [--project PROJECT]
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_eventops_data")


def serialize_firestore_value(val):
    """Normalize Firestore timestamps and non-serializable objects to portable ISO/JSON."""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: serialize_firestore_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [serialize_firestore_value(v) for v in val]
    return val


def export_firestore_data(project_id: str, output_dir: Path, dry_run: bool = False):
    logger.info("Initializing Firestore client for project: %s", project_id)
    db = firestore.Client(project=project_id)

    events_col = db.collection("events")
    event_docs = list(events_col.stream())
    logger.info("Found %d events in Firestore", len(event_docs))

    events_data = []
    all_decisions = []

    for doc in event_docs:
        event_dict = doc.to_dict()
        event_dict["_doc_id"] = doc.id
        event_dict = serialize_firestore_value(event_dict)
        events_data.append(event_dict)

        # Check subcollection 'decisions'
        decisions_ref = doc.reference.collection("decisions")
        decisions_docs = list(decisions_ref.stream())
        logger.info("Event '%s' has %d decisions in ledger", doc.id, len(decisions_docs))

        for dec_doc in decisions_docs:
            dec_dict = dec_doc.to_dict()
            dec_dict["_doc_id"] = dec_doc.id
            dec_dict["event_id"] = dec_dict.get("event_id", doc.id)
            dec_dict = serialize_firestore_value(dec_dict)
            all_decisions.append(dec_dict)

    if dry_run:
        logger.info("[DRY-RUN] Export summary:")
        logger.info("  Total Events: %d", len(events_data))
        logger.info("  Total Decisions: %d", len(all_decisions))
        logger.info("  Target directory: %s", output_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "events.json"
    decisions_path = output_dir / "decisions.json"
    manifest_path = output_dir / "export_manifest.json"

    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events_data, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d events to %s", len(events_data), events_path)

    with open(decisions_path, "w", encoding="utf-8") as f:
        json.dump(all_decisions, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d decisions to %s", len(all_decisions), decisions_path)

    manifest = {
        "export_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_project_id": project_id,
        "events_count": len(events_data),
        "decisions_count": len(all_decisions),
        "event_ids": [e.get("event_id", e.get("_doc_id")) for e in events_data],
        "schema_version": "1.0.0",
        "format": "portable_eventops_json",
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logger.info("Saved export manifest to %s", manifest_path)
    logger.info("Export completed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Export EventOps AI Firestore data to portable JSON")
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-a69f0245a9b4"),
        help="GCP Project ID",
    )
    parser.add_argument(
        "--output-dir",
        default="backups/firestore",
        help="Output directory for JSON export (default: backups/firestore)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry-run check without writing files",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    export_firestore_data(args.project, output_dir, args.dry_run)


if __name__ == "__main__":
    main()
