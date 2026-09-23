# EventOps AI — Enterprise Connected Services & Analytics Guide

## 1. Architectural Overview

EventOps AI connects real-world event coordination workflows with enterprise productivity tools:
1. **Google Calendar**: Main event & Run-of-Show milestone scheduling with drift detection.
2. **Gmail**: Draft-first operational communications with mandatory two-step human confirmation.
3. **Slack**: Structured Block Kit notifications with channel routing and duplicate prevention.
4. **EventOps Analytics**: Deterministic, 4-domain operational telemetry and portfolio analytics with strict privacy filtering.

```
                           +-------------------------------------+
                           |      EventOps Operations Lead       |
                           +-------------------------------------+
                                              |
                          [ Intent / Request  | Human Approval ]
                                              v
+---------------------------------------------------------------------------------+
|                                 EventOps AI Core                                |
|                                                                                 |
|   +--------------------------+               +------------------------------+   |
|   | External Action Ledger   |<------------->| Two-Phase Governance Engine  |   |
|   | (Audit Trail & Status)   |               | (Preview -> Approval -> Exec)|   |
|   +--------------------------+               +------------------------------+   |
|                                                              |                  |
+--------------------------------------------------------------|------------------+
                                                               |
             +--------------------+----------------------------+--------------------+
             |                    |                            |                    |
             v                    v                            v                    v
    +-----------------+  +-----------------+          +-----------------+  +-----------------+
    | Google Calendar |  |  Gmail Service  |          |  Slack Webhook  |  |   4-Domain      |
    |    Provider     |  |    Provider     |          |    Provider     |  |   Analytics     |
    +-----------------+  +-----------------+          +-----------------+  +-----------------+
             |                    |                            |                    |
             v                    v                            v                    v
      [ Cal Sync /         [ Draft First /              [ Block Kit Post /    [ Privacy Ring- |
       Milestones ]         CONFIRM_SEND ]               Deduplication ]       Buffer Metric ]
```

---

## 2. Two-Phase Action Governance Model

EventOps AI strictly adheres to the principle that **AI recommends, humans govern**. The platform never executes side-effecting external mutations silently.

Every external action follows this deterministic lifecycle:

```
Intent / Trigger
       |
       v
Phase 1: Proposal & Structured Preview (Tool / API)
       |
       v
Action Ledger Record Created (`status = pending_approval`)
       |
       +---> Visible in External Action Ledger Table & Copilot
       |
       v
Human Review & Decision
       |
       +---> [ REJECT ] ---> Status = "rejected", Mutation blocked
       |
       v
      [ APPROVE ]
       |
       v
Phase 2: Provider Execution with Idempotency Key
       |
       +---> Gmail Send requires SECOND explicit token: `CONFIRM_SEND`
       |
       v
Action Ledger Updated (`status = completed` or `failed`)
       |
       v
Telemetry Recorded in Analytics (Sanitized Metadata)
```

---

## 3. Connected Services

### A. Google Calendar Integration
- **Purpose**: Synchronize the primary event block or individual Run-of-Show milestones to Google Calendar.
- **Drift & Change Detection**: Generates a cryptographic `sync_hash` across event title, date, start time, and venue. Compares current state against calendar sync state to highlight drift (`out_of_sync`) if time or location changes.
- **Truthful Status**: If `GOOGLE_CALENDAR_CREDENTIALS` is unset, the provider displays **NOT CONFIGURED** rather than falsifying live access.
- **Simulation Mode**: In static demo mode or local development with `EVENTOPS_SIMULATED_INTEGRATIONS=true`, deterministic simulation assigns mock Google Calendar IDs (`gcal_sim_*`) without contacting Google servers.

### B. Gmail Integration
- **Purpose**: Draft and dispatch critical event updates, dietary intake forms, and partner briefings.
- **Draft-First Default**: By default, EventOps AI **only drafts** emails. It never sends immediately.
- **Strict Recipient Validation**: Email addresses are verified against an RFC-compliant regular expression. Empty lists or hallucinated names are rejected with actionable errors before entering the ledger.
- **Two-Step Human Confirmation**: Actually sending an approved draft requires passing `confirmation_token="CONFIRM_SEND"`. If omitted or incorrect, execution is blocked.
- **Truthful Status**: Unconfigured state displays **NOT CONFIGURED** unless `EVENTOPS_SIMULATED_INTEGRATIONS=true` is enabled.

### C. Slack Integration
- **Purpose**: Post operational findings, risk alerts, and decision summaries to team channels (`#event-ops`, `#leadership-briefing`, `#general-announcements`).
- **Structured Formatting**: Formatted in operational Block Kit syntax (Item, Details, Recommended Action, Owner, Due Date, and Deep Link).
- **Duplicate Prevention**: Enforces idempotency keys so repeated clicks or retries do not spam Slack channels.
- **Decision Ledger Share**: Each row in the Decision Ledger features an inline Slack share button to broadcast decisions directly to the team.

---

## 4. EventOps Analytics & 4-Domain Operational Telemetry

EventOps Analytics provides real-time, explainable operational intelligence across 4 distinct domains:

### 1. Event Health Domain
- **Authoritative Readiness Score** (0–100 scale).
- **Risk Severity Breakdown**: Critical risks, attention items, and resolved mitigations.
- **Operational Assumptions**: Active dependencies requiring validation.
- **Guest Attendance**: Confirmed VIP and attendee volume.

### 2. Financial Invariance Domain
- **Total Budget Ceiling & Allocated Budget**: Sum of all category line items.
- **Budget Variance**: Mathematical variance relative to budget limit.
- **Contingency Buffer Health**: Dollar amount and percentage allocated to contingency reserve (alerting if below 8%).

### 3. Governance & Agency Domain
- **Decision Outcomes**: Pending, approved, and rejected decision counts.
- **Executive Approval Rate**: Ratio of approved to reviewed decisions.
- **External Action Ledger Metrics**: Total, completed, pending, and failed integration actions.

### 4. System Reliability & Telemetry Domain
- **Request & Operation Volume**: Count of operations recorded in the ring buffer.
- **Success Rate**: Percentage of external operations and tool invocations completing successfully.
- **Median Latency**: Median response latency in milliseconds.
- **Recent Operations Log**: Chronological trail of recent operations.

---

## 5. Strict Privacy & PII Compliance

EventOps Analytics operates a dedicated non-blocking in-memory ring buffer (default max capacity 1,000 events) that enforces automated PII stripping.

### Stripped Metadata Keys
The following keys are **strictly stripped** before telemetry storage:
- `email`, `emails`, `recipient`, `recipients`, `to`
- `guest_name`, `guest_names`
- `dietary`, `dietary_restrictions`, `allergies`, `accessibility`
- `token`, `access_token`, `client_secret`, `authorization`
- `body`, `raw_prompt`

Attendee names and sensitive medical/dietary details are never logged in operational telemetry. Telemetry stores only anonymized categorical counters, status codes, and latency measurements.

---

## 6. Portfolio Demo Mode (GitHub Pages)

The permanent portfolio version hosted on GitHub Pages:
- Operates 100% in client-side static mode (`DemoEventOpsProvider`).
- Requires **zero external cloud credentials** or paid infrastructure.
- Accurately renders the Connected Services status, Two-Phase Governance Ledger, and 4-Domain Analytics using preserved demo data.
- Does **not** claim live connection to Google Cloud, Vertex AI, or Firestore.
