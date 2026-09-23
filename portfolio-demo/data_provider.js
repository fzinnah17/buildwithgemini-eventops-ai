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

  async updateEvent(eventId, updates) {
    const res = await fetch(`/api/events/${encodeURIComponent(eventId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
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
      if (evt.readiness_score != null) {
        evt.readiness_score = Math.min(100, evt.readiness_score + 5);
      }
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
    const title = (payload.title || "").trim();
    const invalidTitles = ["untitled event", "untitled executive salon", "new event", "untitled"];
    if (!title || invalidTitles.includes(title.toLowerCase())) {
      throw new Error("A meaningful, non-placeholder event title is required.");
    }
    const guestCount = parseInt(payload.guest_count, 10);
    if (isNaN(guestCount) || guestCount <= 0) {
      throw new Error("Guest count must be a positive integer.");
    }
    const totalBudget = parseFloat(payload.total_budget);
    if (isNaN(totalBudget) || totalBudget < 0) {
      throw new Error("Total budget must be a non-negative number.");
    }
    const location = (payload.location || "").trim();
    if (!location) {
      throw new Error("Location cannot be empty.");
    }

    const newId = `evt_${Date.now().toString(36)}`;
    const f_b = Math.round(totalBudget * 0.55 * 100) / 100;
    const contingency = Math.round(totalBudget * 0.10 * 100) / 100;
    const staffing = Math.round(totalBudget * 0.15 * 100) / 100;
    const materials = Math.round(totalBudget * 0.10 * 100) / 100;
    const venue = Math.round((totalBudget - (f_b + contingency + staffing + materials)) * 100) / 100;

    const newEvt = {
      event_id: newId,
      title: title,
      guest_count: guestCount,
      total_budget: totalBudget,
      location: location,
      event_type: payload.event_type || "networking_dinner",
      objective: payload.objective || "Executive networking and strategic alignment",
      protected_priorities: payload.protected_priorities || ["Food & Beverage Quality", "Zero-Variance Budget"],
      status: "planning",
      version: 1,
      readiness_score: 85,
      budget_allocations: [
        { category: "Food & Beverage", allocated_amount: f_b, is_protected: true, notes: "Catering and beverage package" },
        { category: "Venue & Facilities", allocated_amount: venue, is_protected: false, notes: "Space rental or room fee" },
        { category: "Staffing & Hospitality", allocated_amount: staffing, is_protected: false, notes: "Event host and greeters" },
        { category: "Signage & Atmosphere", allocated_amount: materials, is_protected: false, notes: "Print materials and table décor" },
        { category: "Contingency Reserve", allocated_amount: contingency, is_protected: true, notes: "10% unforeseen buffer" }
      ],
      run_of_show: [
        { time: "18:00 - 18:30", activity: "Guest Arrival & Welcome Refreshments", zone: "Foyer", owner: "Event Host", notes: "Acoustics < 65 dBA" },
        { time: "18:30 - 20:00", activity: "Main Program & Curated Discussions", zone: "Dining Room", owner: "Program Director", notes: "Dietary protocols enforced" },
        { time: "20:00 - 21:00", activity: "Dessert, Networking & Closing", zone: "Lounge", owner: "Lead Host", notes: "Zero-proof bar available" }
      ],
      staffing: [
        { role: "Lead Event Director", count: 1, responsibility: "Overall coordination" },
        { role: "Guest Greeting & Coat Check Attendant", count: 1, responsibility: "Arrival management" }
      ],
      risks: [
        { category: "Operations", severity: "Low", details: "Last-minute guest dietary requests", mitigation: "Hold 2 reserve allergen-free plates", status: "open" }
      ],
      guest_journey: [
        { stage: "Arrival", experience: "Warm personal greeting and seamless check-in" },
        { stage: "Main Program", experience: "Engaging, unhurried conversation" },
        { stage: "Departure", experience: "Thoughtful parting takeaway" }
      ],
      atmosphere: {
        statement: "Intimate, warm, and highly conversational environment.",
        attributes: ["Warm", "Curated", "Acoustic Clarity"]
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    newEvt.budget_breakdown = newEvt.budget_allocations;
    this.events.unshift(newEvt);
    return { status: "created", event_id: newId, event: newEvt };
  }

  async updateEvent(eventId, updates) {
    const evt = this.events.find(e => e.event_id === eventId);
    if (!evt) throw new Error(`Event ${eventId} not found.`);

    if (updates.title !== undefined) {
      const t = (updates.title || "").trim();
      const invalid = ["untitled event", "untitled executive salon", "new event", "untitled"];
      if (!t || invalid.includes(t.toLowerCase())) {
        throw new Error("A meaningful, non-placeholder event title is required.");
      }
      evt.title = t;
    }
    if (updates.guest_count !== undefined) {
      const gc = parseInt(updates.guest_count, 10);
      if (isNaN(gc) || gc <= 0) throw new Error("Guest count must be greater than 0.");
      evt.guest_count = gc;
    }
    if (updates.total_budget !== undefined) {
      const tb = parseFloat(updates.total_budget);
      if (isNaN(tb) || tb < 0) throw new Error("Total budget must be non-negative.");
      evt.total_budget = tb;
    }
    if (updates.location !== undefined) {
      const loc = (updates.location || "").trim();
      if (!loc) throw new Error("Location cannot be empty.");
      evt.location = loc;
    }
    if (updates.event_type !== undefined) evt.event_type = updates.event_type;
    if (updates.objective !== undefined) evt.objective = updates.objective;
    if (updates.protected_priorities !== undefined) evt.protected_priorities = updates.protected_priorities;
    if (updates.budget_allocations !== undefined) {
      evt.budget_allocations = updates.budget_allocations;
      evt.budget_breakdown = updates.budget_allocations;
    }
    if (updates.staffing !== undefined) evt.staffing = updates.staffing;
    if (updates.tasks !== undefined) evt.tasks = updates.tasks;
    if (updates.risks !== undefined) evt.risks = updates.risks;
    if (updates.run_of_show !== undefined) evt.run_of_show = updates.run_of_show;
    if (updates.guest_journey !== undefined) evt.guest_journey = updates.guest_journey;
    if (updates.atmosphere !== undefined) evt.atmosphere = updates.atmosphere;

    evt.version = (evt.version || 1) + 1;
    evt.updated_at = new Date().toISOString();
    return { status: "updated", event_id: eventId, version: evt.version, event: evt };
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
    const rejectedDec = this.decisions.filter(d => d.event_id === eventId && d.approval_status === "rejected").length;
    const pendingDec = this.decisions.filter(d => d.event_id === eventId && ["pending", "proposed", "pending_approval"].includes(d.approval_status)).length;
    const totalReviewed = approvedDec + rejectedDec;
    const approvalRate = totalReviewed > 0 ? Math.round((approvedDec / totalReviewed) * 100) : null;

    const completedAct = this.integrationActions.filter(a => a.event_id === eventId && a.status === "completed").length;
    const pendingAct = this.integrationActions.filter(a => a.event_id === eventId && a.status === "pending_approval").length;
    const failedAct = this.integrationActions.filter(a => a.event_id === eventId && a.status === "failed").length;

    const allocations = evt.budget_allocations || evt.budget_breakdown || [];
    const totalAllocated = allocations.reduce((s, b) => s + (Number(b.allocated_amount) || 0), 0);
    const totalBudget = Number(evt.total_budget) || 0;
    const variance = Math.round((totalAllocated - totalBudget) * 100) / 100;
    const contingencyItem = allocations.find(b => (b.category || "").toLowerCase().includes("contingency"));
    const contingencyAmount = contingencyItem ? Number(contingencyItem.allocated_amount) || 0 : 0;
    const contingencyPct = totalBudget > 0 ? Math.round((contingencyAmount / totalBudget) * 1000) / 10 : 0.0;

    const risks = evt.risks || [];
    const criticalRisks = risks.filter(r => (r.severity || "").toLowerCase() === "critical").length;
    const attentionItems = risks.filter(r => ["high", "attention", "medium"].includes((r.severity || "").toLowerCase())).length;
    const resolvedRisks = risks.filter(r => ["resolved", "mitigated"].includes((r.status || "").toLowerCase())).length;

    return {
      status: "ok",
      analytics: {
        scope: "event",
        event_id: eventId,
        title: evt.title || "Event Dossier",
        health: {
          readiness_score: evt.readiness_score != null ? evt.readiness_score : null,
          readiness_trend: evt.readiness_score != null ? (evt.readiness_score >= 90 ? "Stable" : "Attention Required") : "Pending Scan",
          critical_risks: criticalRisks,
          attention_items: attentionItems,
          resolved_risks: resolvedRisks,
          open_assumptions: (evt.assumptions || []).length,
          guest_count: evt.guest_count || 0,
          timeline_milestones_count: (evt.run_of_show || []).length
        },
        financial: {
          total_budget: totalBudget,
          allocated_budget: totalAllocated,
          variance: variance,
          is_zero_variance: variance === 0.0,
          contingency_amount: contingencyAmount,
          contingency_pct: contingencyPct,
          line_items_count: allocations.length,
          allocations: allocations
        },
        governance: {
          pending_decisions: pendingDec,
          approved_decisions: approvedDec,
          rejected_decisions: rejectedDec,
          approval_rate_pct: approvalRate,
          pending_external_actions: pendingAct,
          completed_external_actions: completedAct,
          failed_external_actions: failedAct
        },
        system: {
          telemetry_events_recorded: 0,
          success_rate_pct: null,
          median_latency_ms: null,
          telemetry_status: "DEMO / NOT MEASURED",
          recent_operations: []
        },
        privacy_compliance: {
          pii_filtered: true,
          guest_details_retained: "None (Counters Only)",
          credential_storage: "Excluded from Analytics"
        }
      }
    };
  }

  async getPortfolioAnalytics() {
    const totalBudget = this.events.reduce((s, e) => s + (Number(e.total_budget) || 0), 0);
    const totalGuests = this.events.reduce((s, e) => s + (Number(e.guest_count) || 0), 0);
    const scores = this.events.map(e => e.readiness_score).filter(s => s != null);
    const avgScore = scores.length > 0 ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10 : null;

    const approvedDec = this.decisions.filter(d => d.approval_status === "approved").length;
    const rejectedDec = this.decisions.filter(d => d.approval_status === "rejected").length;
    const pendingDec = this.decisions.filter(d => ["pending", "proposed", "pending_approval"].includes(d.approval_status)).length;
    const totalReviewed = approvedDec + rejectedDec;
    const govRate = totalReviewed > 0 ? Math.round((approvedDec / totalReviewed) * 1000) / 10 : null;

    let totalRisks = 0;
    this.events.forEach(e => {
      totalRisks += (e.risks || []).filter(r => (r.status || "open") === "open").length;
    });

    return {
      status: "ok",
      portfolio: {
        scope: "portfolio",
        summary: {
          events_managed: this.events.length,
          avg_readiness_score: avgScore,
          total_portfolio_budget: Math.round(totalBudget * 100) / 100,
          total_guests_managed: totalGuests,
          total_risks_count: totalRisks
        },
        governance: {
          pending_decisions: pendingDec,
          approved_decisions: approvedDec,
          rejected_decisions: rejectedDec,
          portfolio_approval_rate_pct: govRate,
          total_external_actions: this.integrationActions.length
        },
        events_breakdown: this.events.map(e => ({
          event_id: e.event_id,
          title: e.title,
          readiness_score: e.readiness_score != null ? e.readiness_score : null,
          total_budget: Number(e.total_budget) || 0,
          guest_count: Number(e.guest_count) || 0
        })),
        system_reliability: {
          total_operations: 0,
          success_rate_pct: null,
          median_latency_ms: null,
          telemetry_status: "DEMO / NOT MEASURED"
        },
        generated_at: new Date().toISOString()
      }
    };
  }

  async chat(message, eventId, userId) {
    const q = message.toLowerCase().trim();
    const evt = this.events.find(e => e.event_id === eventId) || this.events[0] || {};
    
    // Demo Scenario 1: Readiness scan / What am I forgetting / Explain readiness
    if (q.includes("forget") || q.includes("guard") || q.includes("readiness") || q.includes("risk") || q.includes("scan") || q.includes("explain")) {
      const score = evt.readiness_score != null ? evt.readiness_score : 90;
      const openRisks = (evt.risks || []).filter(r => (r.status || "open") === "open");
      const milestones = (evt.run_of_show || []).length;
      const totalBudget = Number(evt.total_budget) || 0;
      
      const items = [
        { category: "Budget Invariance", impact: "+25", rationale: `Budget of $${totalBudget.toLocaleString()} verified with zero-variance protection.`, points: 25 },
        { category: "Run of Show Decompression", impact: "+20", rationale: `${milestones} timeline checkpoints checked against transition caps.`, points: 20 },
      ];
      if (openRisks.length > 0) {
        const topRisk = openRisks[0];
        items.push({
          category: topRisk.category || "Operational Risk",
          impact: topRisk.severity && topRisk.severity.toLowerCase() === "critical" ? "-15" : "-5",
          rationale: topRisk.details || topRisk.issue || "Identified operational risk item requiring director attention.",
          points: topRisk.severity && topRisk.severity.toLowerCase() === "critical" ? -15 : -5,
          action_needed: "Review mitigation plan"
        });
      } else {
        items.push({
          category: "Operational Risk Posture",
          impact: "+20",
          rationale: "All event operational gates clear; no unmitigated critical risks.",
          points: 20
        });
      }

      return {
        response_type: "readiness_scan",
        structured: {
          response_type: "readiness_scan",
          is_demo: true,
          summary: `[Demo Simulation] EventOps Guard evaluated "${evt.title || eventId}" against authoritative playbook standards.`,
          readiness_breakdown: {
            score: score,
            explanation: `[Demo Simulation] Operational readiness is ${score}/100 based on active dossier. ${openRisks.length} open risk item(s) detected.`,
            items: items
          }
        }
      };
    }

    // Demo Scenario 2: Budget Rebalance Proposal
    if (q.includes("budget") || q.includes("rebalance") || q.includes("adjust") || q.includes("catering") || q.includes("reduce") || q.includes("cost") || q.includes("cut")) {
      const currBudget = Number(evt.total_budget) || 4000.0;
      const match = message.match(/\$([0-9,]+(?:\.[0-9]{2})?)/);
      let targetBudget = currBudget;
      if (match) {
        const parsed = parseFloat(match[1].replace(/,/g, ""));
        if (!isNaN(parsed) && parsed > 0) {
          if (q.includes("by") || q.includes("cut") || q.includes("reduce by")) {
            targetBudget = Math.max(500, currBudget - parsed);
          } else {
            targetBudget = parsed;
          }
        }
      }

      const contingency = Math.round(targetBudget * 0.10 * 100) / 100;
      const remaining = Math.max(0, targetBudget - contingency);
      const existingAllocs = evt.budget_allocations || evt.budget_breakdown || [];
      const nonContingency = existingAllocs.filter(a => !(a.category || "").toLowerCase().includes("contingency"));

      const lines = [];
      let allocatedSoFar = 0;
      if (nonContingency.length > 0) {
        const totalExistingNonCont = nonContingency.reduce((s, a) => s + (Number(a.allocated_amount) || 0), 0) || 1;
        nonContingency.forEach((a, i) => {
          let amt;
          if (i === nonContingency.length - 1) {
            amt = Math.round((remaining - allocatedSoFar) * 100) / 100;
          } else {
            const share = (Number(a.allocated_amount) || 0) / totalExistingNonCont;
            amt = Math.round(remaining * share * 100) / 100;
            allocatedSoFar += amt;
          }
          lines.push(`${a.category} ($${amt.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})`);
        });
      } else {
        const cat1 = Math.round(remaining * 0.55 * 100) / 100;
        const cat2 = Math.round(remaining * 0.30 * 100) / 100;
        const cat3 = Math.round((remaining - cat1 - cat2) * 100) / 100;
        lines.push(`Catering & Hospitality ($${cat1.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})`);
        lines.push(`Venue & Staging ($${cat2.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})`);
        lines.push(`AV & Production ($${cat3.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})`);
      }
      lines.push(`Contingency Reserve ($${contingency.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})})`);

      const decId = `dec_${Math.random().toString(36).substring(2, 8)}`;
      const dec = {
        decision_id: decId,
        event_id: evt.event_id || eventId,
        proposed_change: `[Demo Simulation] Rebalance budget for ${evt.title || 'event'}: ${lines.join(", ")}`,
        rationale: `Rebalance total allocations to $${targetBudget.toLocaleString()} while protecting 10% contingency safety buffer ($${contingency.toLocaleString()}) and core priorities.`,
        approval_status: "pending_approval",
        expected_impact: `Zero-variance budget ($${targetBudget.toLocaleString()}) with exactly 10.0% contingency reserve.`,
        timestamp: new Date().toISOString()
      };
      this.decisions.unshift(dec);

      return {
        response_type: "budget_proposal",
        structured: {
          response_type: "budget_proposal",
          is_demo: true,
          decision_id: decId,
          title: `[Demo Simulation] Budget Rebalance Proposed (${evt.title || eventId})`,
          summary: dec.proposed_change
        }
      };
    }

    // Demo Scenario 3: Staffing ratio playbook check
    if (q.includes("staff") || q.includes("ratio") || q.includes("coverage")) {
      const guestCount = Number(evt.guest_count) || 0;
      const staffList = evt.staffing || [];
      const totalStaff = staffList.reduce((sum, s) => sum + (Number(s.count) || 1), 0);
      const ratio = totalStaff > 0 ? Math.round((guestCount / totalStaff) * 10) / 10 : 0;
      const isGap = ratio > 8.0;
      const gapText = isGap ? `${(ratio - 8.0).toFixed(1)} guests/staff above 1:8 target` : "Within target policy buffer";
      const rolesText = staffList.length > 0 
        ? staffList.map(s => `${s.count || 1} ${s.role || 'Staff'}`).join(", ") 
        : "Operational delivery staff";

      return {
        response_type: "informational",
        is_demo: true,
        parts: [
          {
            kind: "text",
            text: `### 👥 [Demo Simulation] Event Operations Playbook: Staffing Analysis\n\n• **Event**: ${evt.title || eventId}\n• **Current**: ${guestCount} guests / ${totalStaff} staff = **1 : ${ratio}**\n• **Active Staff Allocation**: ${rolesText}\n• **Policy Target**: **1 : 8** (VIP Seated Dining & Reception Standards)\n• **Assessment**: **${gapText}**\n\nCoverage across guest arrival, floor service, and culinary coordination is verified against event parameters.`
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
          text: `[Demo Simulation] EventOps Copilot is operating in Portfolio Demo Mode for "${evt.title || eventId}". Use the prompt shortcuts above to trigger verified operational workflows.`
        }
      ]
    };
  }
}

// Global registrations
window.EventOpsDataProvider = EventOpsDataProvider;
window.CloudEventOpsProvider = CloudEventOpsProvider;
window.DemoEventOpsProvider = DemoEventOpsProvider;
