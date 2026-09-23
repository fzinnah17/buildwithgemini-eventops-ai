# EventOps AI — Google Cloud Infrastructure Migration Guide

This guide details how to reproduce and deploy the entire EventOps AI enterprise system in **any new Google Cloud project** from scratch.

---

## 1. Prerequisites & Tooling

Before starting, ensure your local development machine or cloud workstation has:
- **Google Cloud SDK (`gcloud`)** 480.0.0+
- **Python 3.11+** (recommended: Python 3.13 with `uv`)
- **Node.js 18+** (for UI test and Playwright automation)
- **Git**
- Active Google Cloud Billing Account attached to your target project

```bash
# Set your target project ID and region
export TARGET_PROJECT="your-new-gcp-project-id"
export TARGET_REGION="us-central1"
gcloud config set project "$TARGET_PROJECT"
```

---

## 2. Enable Required Google Cloud APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com
```

---

## 3. Least-Privilege IAM Architecture

### Workshop Temporary IAM vs. Production Persistent IAM

| Service / Principal | Workshop Mode (Lab) | Recommended Production Mode (Least Privilege) |
| :--- | :--- | :--- |
| **Cloud Run Service Account** | Compute Default Service Account | Dedicated `eventops-frontend-sa@${PROJECT}.iam.gserviceaccount.com` |
| **Reasoning Engine Service Account** | Compute Default Service Account | Dedicated `eventops-agent-sa@${PROJECT}.iam.gserviceaccount.com` |
| **Firestore Access** | Project Editor | `roles/datastore.user` (scoped strictly to `events` collections) |
| **Cloud Storage Media Access** | Project Editor | `roles/storage.objectAdmin` on specific `eventops-ai-media-*` bucket |
| **Vertex AI Prediction** | Project Editor | `roles/aiplatform.user` |

### Setting Up Dedicated Production Service Accounts

```bash
# 1. Create Cloud Run Frontend Service Account
gcloud iam service-accounts create eventops-frontend-sa \
  --display-name="EventOps AI Frontend Service Account"

# 2. Grant permissions to call Vertex AI Reasoning Engine and Firestore
gcloud projects add-iam-policy-binding "$TARGET_PROJECT" \
  --member="serviceAccount:eventops-frontend-sa@${TARGET_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding "$TARGET_PROJECT" \
  --member="serviceAccount:eventops-frontend-sa@${TARGET_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding "$TARGET_PROJECT" \
  --member="serviceAccount:eventops-frontend-sa@${TARGET_PROJECT}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

---

## 4. Cloud Firestore Initialization & Data Restoration

1. Initialize Firestore in **Native Mode**:
```bash
gcloud firestore databases create --location="$TARGET_REGION" --type=firestore-native
```

2. Restore the portable event dossiers and decision records:
```bash
# Test with a dry run first
uv run python scripts/import_eventops_data.py --project "$TARGET_PROJECT" --dry-run

# Perform real restoration
uv run python scripts/import_eventops_data.py --project "$TARGET_PROJECT" --overwrite
```

---

## 5. Cloud Storage Media Bucket Setup

```bash
export MEDIA_BUCKET="eventops-ai-media-${TARGET_PROJECT}"
gcloud storage buckets create "gs://${MEDIA_BUCKET}" --location="$TARGET_REGION" --uniform-bucket-level-access

# Allow public read access for event moodboards and visual concept renders
gcloud storage buckets add-iam-policy-binding "gs://${MEDIA_BUCKET}" \
  --member="allUsers" \
  --role="roles/storage.objectViewer"

# Upload preserved visual assets
gcloud storage cp -r assets/generated/* "gs://${MEDIA_BUCKET}/events/evt_wit_manhattan_2026/"
```

---

## 6. Serverless Vertex AI RAG Corpus Setup

Run the automated bootstrapping script to upload the operational playbook to GCS, configure the Serverless Vector DB, create the corpus, and index with `gemini-2.5-flash`:

```bash
uv run python scripts/create_rag_corpus.py \
  --project "$TARGET_PROJECT" \
  --location "$TARGET_REGION" \
  --bucket "$MEDIA_BUCKET"
```
*Note: This automatically creates or updates `app/rag_config.py` with your new corpus URI.*

---

## 7. Vertex AI Memory Bank Setup

1. Create a Memory Bank instance using the Vertex AI Agent Engine CLI or Python SDK:
```python
import vertexai
from vertexai.preview import rag

# Memory Bank ID is assigned upon provisioning
# Save the resulting ID to your environment
```

2. Export the Memory Bank ID:
```bash
export MEMORY_BANK_ID="<your-new-memory-bank-id>"
export MEMORY_SERVICE_URI="agentengine://${MEMORY_BANK_ID}"
```

---

## 8. Deploy Vertex AI Agent Platform Reasoning Engine

Deploy the agent backend using the Google Agent Development Kit (ADK) CLI:

```bash
uv run agents-cli deploy \
  --project "$TARGET_PROJECT" \
  --region "$TARGET_REGION"
```

Capture the printed Reasoning Engine resource name (format: `projects/{PROJECT_NUMBER}/locations/{REGION}/reasoningEngines/{ENGINE_ID}`).

---

## 9. Deploy Cloud Run Frontend

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/us-central1/reasoningEngines/..."

gcloud run deploy eventops-ai-frontend \
  --source . \
  --region "$TARGET_REGION" \
  --allow-unauthenticated \
  --service-account "eventops-frontend-sa@${TARGET_PROJECT}.iam.gserviceaccount.com" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${TARGET_PROJECT},GOOGLE_CLOUD_LOCATION=${TARGET_REGION},AGENT_ENGINE_RESOURCE_NAME=${AGENT_ENGINE_RESOURCE_NAME},EVENTOPS_MEDIA_BUCKET=${MEDIA_BUCKET},PORT=8080"
```

---

## 10. Post-Migration Verification Checklist

- [ ] `GET /api/events` returns all 3 seeded events (`evt_wit_manhattan_2026`, `evt_design_summit_2026`, `evt_exec_dinner_manhattan_2024`).
- [ ] Active event switching re-renders Dossier, Readiness score, and Decision Ledger.
- [ ] Copilot query (`"What am I forgetting?"`) returns structured EventOps Guard cards.
- [ ] Budget rebalancing calculates exact zero variance ($\sum \text{allocations} == \text{total\_budget}$).
- [ ] Decision approval (`POST /api/decisions/approve`) updates Firestore and ledger status.
- [ ] Visual direction images load from Cloud Storage bucket.
- [ ] Error sanitization returns clean `request_id` on internal fault injection.

---

## 11. Enterprise Connected Services & Analytics (Bundle 3.6)

EventOps AI includes built-in two-phase action governance and deterministic operational analytics.

### Optional Integration Environment Variables

```bash
# Safe simulation mode (Default: true if credentials absent)
export EVENTOPS_SIMULATED_INTEGRATIONS="true"

# Google Calendar (Service Account or OAuth client secrets JSON)
export GOOGLE_CALENDAR_CREDENTIALS="/path/to/credentials.json"

# Gmail API (OAuth client secrets JSON)
export GMAIL_CREDENTIALS="/path/to/gmail_credentials.json"

# Slack Integration (Incoming Webhook or Bot Token)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export SLACK_BOT_TOKEN="your-slack-bot-token"
```

### Connected Services Verification

- [ ] `GET /api/integrations/status` reports truthful connection states.
- [ ] Action proposals create `pending_approval` entries in the External Action Ledger.
- [ ] Calendar sync computes `sync_hash` for drift detection.
- [ ] Email operations require two-step `CONFIRM_SEND` token confirmation.
- [ ] Slack notifications format as operational Block Kit and prevent duplicate posts.
- [ ] `GET /api/analytics/event/{event_id}` returns 4-domain metrics with PII sanitization.
- [ ] `GET /api/analytics/portfolio` aggregates operational health across all managed events.

