// EventOps AI — Data Provider Abstraction Layer
// Supports dual runtime modes: Cloud Live vs Zero-Cost Portfolio Demo

class EventOpsDataProvider {
  async listEvents() { throw new Error("listEvents() not implemented"); }
  async getEvent(eventId) { throw new Error("getEvent() not implemented"); }
  async approveDecision(decisionId, eventId) { throw new Error("approveDecision() not implemented"); }
  async rejectDecision(decisionId, eventId) { throw new Error("rejectDecision() not implemented"); }
  async createEvent(payload) { throw new Error("createEvent() not implemented"); }
  async chat(message, eventId, userId) { throw new Error("chat() not implemented"); }
  async getIntegrationsStatus() { throw new Error("getIntegrationsStatus() not implemented"); }
  async getIntegrationActions(eventId) { throw new Error("getIntegrationActions() not implemented"); }
  async previewCalendar(eventId, mode) { throw new Error("previewCalendar() not implemented"); }
  async syncCalendar(eventId, actionId) { throw new Error("syncCalendar() not implemented"); }
  async draftEmail(eventId, intent, recipients) { throw new Error("draftEmail() not implemented"); }
  async saveEmailDraft(eventId, actionId) { throw new Error("saveEmailDraft() not implemented"); }
  async sendEmail(eventId, actionId, confirmationToken) { throw new Error("sendEmail() not implemented"); }
  async previewSlack(eventId, category, item, channel) { throw new Error("previewSlack() not implemented"); }
  async postSlack(eventId, actionId) { throw new Error("postSlack() not implemented"); }
  async approveIntegrationAction(eventId, actionId) { throw new Error("approveIntegrationAction() not implemented"); }
  async rejectIntegrationAction(eventId, actionId) { throw new Error("rejectIntegrationAction() not implemented"); }
  async getEventAnalytics(eventId) { throw new Error("getEventAnalytics() not implemented"); }
  async getPortfolioAnalytics() { throw new Error("getPortfolioAnalytics() not implemented"); }
}

class CloudEventOpsProvider extends EventOpsDataProvider {
  async listEvents() {
    const res = await fetch("/api/events");
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async getEvent(eventId) {
    const res = await fetch(`/api/event/${eventId}`);
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async approveDecision(decisionId, eventId) {
    const res = await fetch("/api/decisions/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision_id: decisionId, event_id: eventId })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async rejectDecision(decisionId, eventId) {
    const res = await fetch("/api/decisions/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision_id: decisionId, event_id: eventId })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async createEvent(payload) {
    const res = await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async chat(message, eventId, userId) {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, event_id: eventId, user_id: userId })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async getIntegrationsStatus() {
    const res = await fetch("/api/integrations/status");
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async getIntegrationActions(eventId) {
    const res = await fetch(`/api/integrations/actions?event_id=${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async previewCalendar(eventId, mode) {
    const res = await fetch("/api/integrations/calendar/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, mode: mode || "main" })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async syncCalendar(eventId, actionId) {
    const res = await fetch("/api/integrations/calendar/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, action_id: actionId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  }

  async draftEmail(eventId, intent, recipients) {
    const res = await fetch("/api/integrations/email/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, intent: intent, recipients: recipients })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  }

  async saveEmailDraft(eventId, actionId) {
    const res = await fetch("/api/integrations/email/save-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, action_id: actionId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  }

  async sendEmail(eventId, actionId, confirmationToken) {
    const res = await fetch("/api/integrations/email/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, action_id: actionId, confirmation_token: confirmationToken })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  }

  async previewSlack(eventId, category, item, channel) {
    const res = await fetch("/api/integrations/slack/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, category: category, item: item, channel: channel || "#event-ops" })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async postSlack(eventId, actionId) {
    const res = await fetch("/api/integrations/slack/post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, action_id: actionId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return await res.json();
  }

  async approveIntegrationAction(eventId, actionId) {
    const res = await fetch(`/api/integrations/actions/${encodeURIComponent(actionId)}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async rejectIntegrationAction(eventId, actionId) {
    const res = await fetch(`/api/integrations/actions/${encodeURIComponent(actionId)}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId })
    });
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async getEventAnalytics(eventId) {
    const res = await fetch(`/api/analytics/event/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }

  async getPortfolioAnalytics() {
    const res = await fetch("/api/analytics/portfolio");
    if (!res.ok) throw new Error(`Live API error: HTTP ${res.status}`);
    return await res.json();
  }
}

class DemoEventOpsProvider extends EventOpsDataProvider {
  constructor(initialEvents, initialDecisions) {
    super();
    this.events = JSON.parse(JSON.stringify(initialEvents || window.EVENTOPS_DEFAULT_EVENTS || []));
    this.decisions = JSON.parse(JSON.stringify(initialDecisions || window.EVENTOPS_DEFAULT_DECISIONS || []));
    this.integrationActions = [];
  }

  async listEvents() {
    return this.events.map(e => ({
      event_id: e.event_id,
      title: e.title,
      status: e.status || "planning",
      guest_count: e.guest_count,
      total_budget: e.total_budget,
      readiness_score: e.readiness_score || 95
    }));
  }

  async getEvent(eventId) {
    const evt = this.events.find(e => e.event_id === eventId);
    if (!evt) {
      if (this.events.length > 0) return this.getEvent(this.events[0].event_id);
      throw new Error(`Event ${eventId} not found in fixtures`);
    }
    const copy = JSON.parse(JSON.stringify(evt));
    copy.decisions = this.decisions.filter(d => d.event_id === eventId);
    return copy;
  }

  async approveDecision(decisionId, eventId) {
    const dec = this.decisions.find(d => d.decision_id === decisionId);
    if (dec) {
      dec.approval_status = "approved";
      dec.approved_by = "demo-organizer";
      dec.approval_timestamp = new Date().toISOString();
    }
    const evt = this.events.find(e => e.event_id === eventId);
    if (evt) {
      evt.version = (evt.version || 1) + 1;
      evt.readiness_score = Math.min(100, (evt.readiness_score || 85) + 5);
    }
    return {
      status: "approved",
      decision_id: decisionId,
      idempotency_status: "executed",
      message: `Simulated decision committed to local demo dossier (v${evt ? evt.version : 2}). No external cloud state was modified.`
    };
  }

  async rejectDecision(decisionId, eventId) {
    const dec = this.decisions.find(d => d.decision_id === decisionId);
    if (dec) {
      dec.approval_status = "rejected";
      dec.approved_by = "demo-organizer";
      dec.approval_timestamp = new Date().toISOString();
    }
    return {
      status: "rejected",
      decision_id: decisionId,
      idempotency_status: "executed",
      message: "Simulated decision rejected. Local operational state preserved."
    };
  }

  async createEvent(payload) {
    const newId = `evt_${Date.now().toString(36)}`;
    const totalBudget = Number(payload.total_budget) || 5000.0;
    const newEvt = {
      event_id: newId,
      title: payload.title || "Untitled Executive Salon",
      guest_count: Number(payload.guest_count) || 30,
      total_budget: totalBudget,
      location: payload.location || "New York, NY",
      status: "planning",
      version: 1,
      readiness_score: 85,
      budget_allocations: [
        { category: "Venue Rental & Staff", allocated_amount: totalBudget * 0.35 },
        { category: "Catering & Beverage Program", allocated_amount: totalBudget * 0.40 },
        { category: "AV & Acoustic Production", allocated_amount: totalBudget * 0.15 },
        { category: "Contingency Reserve (10%)", allocated_amount: totalBudget * 0.10 }
      ],
      run_of_show: [
        { time: "18:00 - 18:45", activity: "Guest Arrival & Decompression", zone: "Foyer", notes: "Acoustics < 65 dBA" },
        { time: "18:45 - 20:30", activity: "Curated Seated Dinner & Salon", zone: "Dining Room", notes: "Dietary protocols enforced" },
        { time: "20:30 - 21:30", activity: "Dessert & Strategic Networking", zone: "Lounge", notes: "Zero-proof bar available" }
      ],
      readiness_breakdown: {
        score: 85,
        explanation: "Initial dossier drafted. Dietary restrictions and venue sound checks required.",
        items: [
          { category: "Budget Governance", impact: "+25", rationale: "Exact zero-variance budget allocated.", points: 25 },
          { category: "Staffing Ratio", impact: "+20", rationale: "Standard 1:8 guest-to-staff ratio planned.", points: 20 },
          { category: "Dietary Inclusion", impact: "-10", rationale: "Dietary intake survey not yet finalized.", points: -10, action_needed: "Finalize dietary intake" },
          { category: "Acoustic Noise Floor", impact: "-5", rationale: "Pre-dinner acoustic verification pending.", points: -5, action_needed: "Confirm venue noise rating" }
        ]
      }
    };
    this.events.unshift(newEvt);
    return { status: "created", event_id: newId };
  }

  async getIntegrationsStatus() {
    return {
      status: "ok",
      integrations: [
        {
          provider: "google_calendar",
          status: "demo_simulated",
          display_name: "Google Calendar",
          is_demo: true,
          scopes: ["https://www.googleapis.com/auth/calendar.events"],
          target_calendar: "primary (simulated)",
          details: "Portfolio Demo simulation active. No live calendar credentials required."
        },
        {
          provider: "gmail",
          status: "demo_simulated",
          display_name: "Gmail (Drafts & Communications)",
          is_demo: true,
          scopes: ["https://www.googleapis.com/auth/gmail.compose"],
          details: "Portfolio Demo simulation active. Drafts generated safely without sending."
        },
        {
          provider: "slack",
          status: "demo_simulated",
          display_name: "Slack Operations",
          is_demo: true,
          default_channel: "#event-ops",
          details: "Portfolio Demo simulation active. Formatted operational cards previewed locally."
        }
      ]
    };
  }

  async getIntegrationActions(eventId) {
    return {
      status: "ok",
      event_id: eventId,
      actions: this.integrationActions.filter(a => a.event_id === eventId)
    };
  }

  async previewCalendar(eventId, mode) {
    const evt = await this.getEvent(eventId);
    const actionId = `act_${Math.random().toString(36).substring(2, 9)}`;
    const preview = {
      is_demo: true,
      summary: `[Demo Simulation] ${evt.title || "Executive Dinner"}`,
      start_time: `${evt.date || "2026-10-15"}T18:00:00Z`,
      end_time: `${evt.date || "2026-10-15"}T21:30:00Z`,
      location: evt.location || "New York, NY",
      description: `Governed Event Operations sync by EventOps AI.\nGuest Count: ${evt.guest_count || 30}\nBudget: $${(evt.total_budget || 4000).toLocaleString()}`,
      entries_count: (mode === "milestones" && evt.run_of_show) ? evt.run_of_show.length : 1
    };
    const action = {
      action_id: actionId,
      event_id: eventId,
      provider: "calendar",
      action_type: mode === "milestones" ? "sync_milestones" : "create_event",
      target: "primary_calendar",
      preview: preview,
      status: "pending_approval",
      requested_at: new Date().toISOString(),
      is_demo: true
    };
    this.integrationActions.unshift(action);
    return { status: "ok", action, preview };
  }

  async syncCalendar(eventId, actionId) {
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    if (act.status !== "approved") throw new Error("Action must be approved by director before syncing.");
    act.status = "completed";
    act.executed_at = new Date().toISOString();
    act.external_resource_id = `cal_sim_${Date.now()}`;
    return {
      status: "completed",
      is_demo: true,
      action_id: actionId,
      calendar_event_id: act.external_resource_id,
      html_link: "https://calendar.google.com/calendar/r?demo=true",
      message: "[Demo Simulation] Calendar event synchronized to local demo timeline."
    };
  }

  async draftEmail(eventId, intent, recipients) {
    if (!recipients || recipients.length === 0) throw new Error("Recipient email required. Do not infer it from a person's name.");
    const validRecipients = recipients.filter(r => r.includes("@"));
    if (validRecipients.length === 0) throw new Error("Invalid recipient email address format.");
    const evt = await this.getEvent(eventId);
    const draftId = `act_${Math.random().toString(36).substring(2, 9)}`;
    const draft = {
      is_demo: true,
      subject: `[EventOps Demo] Operational Update: ${evt.title || "Dinner"} - ${intent}`,
      to_recipients: validRecipients,
      purpose: intent,
      body_text: `Dear Guest,\n\nWe are preparing for ${evt.title || "the executive dinner"} on ${evt.date || "October 15, 2026"} at ${evt.location || "New York, NY"}.\n\nOperational Notice: ${intent}.\nPlease reply with any specific dietary restrictions or accessibility needs.\n\nWarm regards,\nEvent Operations Team`,
      governance_notice: "[Demo Simulation] Generated draft for human review. No live email sent."
    };
    const action = {
      action_id: draftId,
      event_id: eventId,
      provider: "gmail",
      action_type: "save_draft",
      target: validRecipients.join(", "),
      preview: draft,
      status: "pending_approval",
      requested_at: new Date().toISOString(),
      is_demo: true
    };
    this.integrationActions.unshift(action);
    return { status: "ok", action, draft };
  }

  async saveEmailDraft(eventId, actionId) {
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    if (act.status !== "approved") throw new Error("Action must be approved before saving to Gmail drafts.");
    act.status = "completed";
    act.executed_at = new Date().toISOString();
    act.external_resource_id = `draft_sim_${Date.now()}`;
    return {
      status: "completed",
      is_demo: true,
      action_id: actionId,
      gmail_draft_id: act.external_resource_id,
      message: "[Demo Simulation] Draft saved to simulated Gmail storage. Not sent to guests."
    };
  }

  async sendEmail(eventId, actionId, confirmationToken) {
    if (confirmationToken !== "CONFIRM_SEND") {
      throw new Error("Explicit second confirmation token 'CONFIRM_SEND' required to send email.");
    }
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    act.status = "completed";
    act.executed_at = new Date().toISOString();
    return {
      status: "completed",
      is_demo: true,
      action_id: actionId,
      message: "[Demo Simulation] Email dispatch confirmed by director with secondary confirmation token. Simulation completed."
    };
  }

  async previewSlack(eventId, category, item, channel) {
    const evt = await this.getEvent(eventId);
    const actionId = `act_${Math.random().toString(36).substring(2, 9)}`;
    const chan = channel || "#event-ops";
    const payload = {
      is_demo: true,
      channel: chan,
      header: `[EventOps Operational Alert] ${evt.title || "Dinner"} · ${category}`,
      blocks: [
        { type: "header", text: `[Demo] ${category}: ${item.title || "Operational Notice"}` },
        { type: "section", text: item.summary || item.details || "Operational review required." },
        { type: "context", text: `Event: ${evt.title || "Dinner"} | Target Channel: ${chan}` }
      ],
      recommended_action: item.action || "Review in EventOps Decision Ledger."
    };
    const action = {
      action_id: actionId,
      event_id: eventId,
      provider: "slack",
      action_type: "post_slack_message",
      target: chan,
      preview: payload,
      status: "pending_approval",
      requested_at: new Date().toISOString(),
      is_demo: true
    };
    this.integrationActions.unshift(action);
    return { status: "ok", action, payload };
  }

  async postSlack(eventId, actionId) {
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    if (act.status !== "approved") throw new Error("Action must be approved before posting to Slack.");
    act.status = "completed";
    act.executed_at = new Date().toISOString();
    act.external_resource_id = `ts_sim_${Date.now()}`;
    return {
      status: "completed",
      is_demo: true,
      action_id: actionId,
      channel: act.target,
      message_ts: act.external_resource_id,
      message: `[Demo Simulation] Operational card posted to ${act.target}.`
    };
  }

  async approveIntegrationAction(eventId, actionId) {
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    act.status = "approved";
    act.approved_at = new Date().toISOString();
    return { status: "approved", action_id: actionId, message: "Action approved by director." };
  }

  async rejectIntegrationAction(eventId, actionId) {
    const act = this.integrationActions.find(a => a.action_id === actionId);
    if (!act) throw new Error(`Action ${actionId} not found.`);
    act.status = "rejected";
    return { status: "rejected", action_id: actionId, message: "Action rejected. Preserved in ledger." };
  }

  async getEventAnalytics(eventId) {
    const evt = await this.getEvent(eventId);
    const approvedDec = this.decisions.filter(d => d.event_id === eventId && d.approval_status === "approved").length;
    const totalDec = this.decisions.filter(d => d.event_id === eventId).length;
    const completedAct = this.integrationActions.filter(a => a.event_id === eventId && a.status === "completed").length;
    const totalAct = this.integrationActions.filter(a => a.event_id === eventId).length;

    return {
      status: "ok",
      analytics: {
        event_id: eventId,
        title: evt.title,
        domains: {
          event_health: {
            readiness_score: evt.readiness_score || 95,
            readiness_trend: "improving",
            unresolved_risks_count: (evt.risks || []).filter(r => r.status === "open").length,
            timeline_milestones_count: (evt.run_of_show || []).length,
            days_to_event: 22
          },
          financial: {
            total_budget: evt.total_budget || 4000.0,
            allocated_budget: (evt.budget_allocations || []).reduce((s, b) => s + (b.allocated_amount || 0), 0),
            contingency_reserve_amount: 400.0,
            contingency_reserve_pct: 10.0,
            variance_amount: 0.0,
            variance_pct: 0.0
          },
          governance: {
            total_decisions_proposed: totalDec,
            decisions_approved: approvedDec,
            decisions_rejected: this.decisions.filter(d => d.event_id === eventId && d.approval_status === "rejected").length,
            human_approval_rate_pct: totalDec > 0 ? Math.round((approvedDec / totalDec) * 100) : 100.0,
            integration_actions_proposed: totalAct,
            integration_actions_completed: completedAct,
            governance_compliance_pct: 100.0
          },
          system_reliability: {
            system_uptime_pct: 100.0,
            average_agent_latency_ms: 320,
            error_rate_pct: 0.0,
            total_governed_operations: totalDec + totalAct
          }
        },
        privacy_guarantee: "100% PII-free operational telemetry. No recipient emails, tokens, or raw bodies stored.",
        is_demo: true
      }
    };
  }

  async getPortfolioAnalytics() {
    const totalBudget = this.events.reduce((s, e) => s + (e.total_budget || 0), 0);
    const avgScore = this.events.length > 0 ? Math.round(this.events.reduce((s, e) => s + (e.readiness_score || 90), 0) / this.events.length) : 95;
    return {
      status: "ok",
      portfolio: {
        portfolio_summary: {
          total_events_managed: this.events.length,
          average_readiness_score: avgScore,
          total_budget_governed: totalBudget,
          active_operational_risks: 1
        },
        governance_aggregate: {
          total_decisions_evaluated: this.decisions.length,
          approval_rate_pct: 100.0,
          governed_external_actions: this.integrationActions.length
        },
        privacy_compliance: "Deterministic aggregation with strict PII filtering.",
        is_demo: true
      }
    };
  }

  async chat(message, eventId, userId) {
    const q = message.toLowerCase().trim();
    
    // Demo Scenario 1: Readiness scan / What am I forgetting
    if (q.includes("forget") || q.includes("guard") || q.includes("readiness") || q.includes("risk") || q.includes("scan")) {
      return {
        response_type: "readiness_scan",
        structured: {
          response_type: "readiness_scan",
          is_demo: true,
          summary: "[Demo Simulation] EventOps Guard evaluated the preserved event dossier against the authoritative playbook standards.",
          readiness_breakdown: {
            score: 95,
            explanation: "[Demo Simulation] Operational readiness is 95/100 based on preserved dossier. 1 minor attention item flagged for arrival buffer.",
            items: [
              { category: "Budget Invariance", impact: "+25", rationale: "Exact zero-variance budget balance maintained with 10% safety reserve.", points: 25 },
              { category: "Run of Show Decompression", impact: "+20", rationale: "Arrival buffer and speaker transition caps verified against playbook.", points: 20 },
              { category: "Dietary & Allergen Protocol", impact: "+20", rationale: "Zero-proof beverage pairings and cross-contamination rules defined.", points: 20 },
              { category: "Acoustic Noise Floor", impact: "-5", rationale: "Pre-dinner cocktail area sound check pending at venue.", points: -5, action_needed: "Verify acoustic baffles" }
            ]
          }
        }
      };
    }

    // Demo Scenario 2: Budget Rebalance Proposal
    if (q.includes("budget") || q.includes("rebalance") || q.includes("adjust") || q.includes("catering") || q.includes("reduce") || q.includes("cost")) {
      const decId = `dec_${Math.random().toString(36).substring(2, 8)}`;
      const dec = {
        decision_id: decId,
        event_id: eventId,
        proposed_change: "[Demo Simulation] Rebalance budget: Catering ($1,800.00), Venue ($1,200.00), AV ($600.00), Contingency ($400.00)",
        rationale: "Realign allocations to guarantee mandatory 10% safety contingency reserve while maintaining high culinary standards.",
        approval_status: "pending_approval",
        expected_impact: "Restores safety margin to 10.0% without exceeding $4,000 ceiling.",
        timestamp: new Date().toISOString()
      };
      this.decisions.unshift(dec);
      return {
        response_type: "budget_proposal",
        structured: {
          response_type: "budget_proposal",
          is_demo: true,
          decision_id: decId,
          title: "[Demo Simulation] Budget Rebalance Proposed",
          summary: dec.proposed_change
        }
      };
    }

    // Demo Scenario 3: Staffing ratio playbook check
    if (q.includes("staff") || q.includes("ratio") || q.includes("coverage")) {
      return {
        response_type: "informational",
        is_demo: true,
        parts: [
          {
            kind: "text",
            text: "[Demo Simulation] Event Operations Playbook Rule (Staffing):\n• Seated VIP dinners require a 1:8 guest-to-staff ratio.\n• For 28 guests, minimum 4 dedicated service staff + 1 culinary lead are required.\n• The preserved dossier allocates 4 servers + 1 event lead, which satisfies the operational standard."
          }
        ]
      };
    }

    // Free-form fallback: Gracefully disable arbitrary chat and guide to demo scenarios
    return {
      response_type: "demo_notice",
      is_demo: true,
      parts: [
        {
          kind: "text",
          text: "Live AI Copilot is unavailable in Portfolio Demo Mode. Choose one of the demo scenarios above to explore the workflow."
        }
      ]
    };
  }
}

// Global registrations
window.EventOpsDataProvider = EventOpsDataProvider;
window.CloudEventOpsProvider = CloudEventOpsProvider;
window.DemoEventOpsProvider = DemoEventOpsProvider;
