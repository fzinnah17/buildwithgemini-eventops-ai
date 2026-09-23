import json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
events_file = repo_root / "backups" / "firestore" / "events.json"
decisions_file = repo_root / "backups" / "firestore" / "decisions.json"

with open(events_file, "r") as f:
    events = json.load(f)

with open(decisions_file, "r") as f:
    decisions = json.load(f)

js_content = f"""// EventOps AI — Standalone Portable Demo Fixtures
// Generated from authoritative Firestore backup
window.EVENTOPS_DEFAULT_EVENTS = {json.dumps(events, indent=2)};

window.EVENTOPS_DEFAULT_DECISIONS = {json.dumps(decisions, indent=2)};
"""

target_js = repo_root / "portfolio-demo" / "data" / "fixtures.js"
target_js.parent.mkdir(parents=True, exist_ok=True)
with open(target_js, "w") as f:
    f.write(js_content)

print(f"Successfully generated {target_js} with {len(events)} events and {len(decisions)} decisions.")
