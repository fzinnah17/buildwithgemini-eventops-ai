// EventOps AI — Data Provider Abstraction Layer
// Supports dual runtime modes: Cloud Live vs Zero-Cost Portfolio Demo

class EventOpsDataProvider {
  async listEvents() { throw new Error("listEvents() not implemented"); }
  async getEvent(eventId) { throw new Error("getEvent() not implemented"); }
  async approveDecision(decisionId, eventId) { throw new Error("approveDecision() not implemented"); }
  async rejectDecision(decisionId, eventId) { throw new Error("rejectDecision() not implemented"); }
  async createEvent(payload) { throw new Error("createEvent() not implemented"); }
  async chat(message, eventId, userId) { throw new Error("chat() not implemented"); }
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
}

class DemoEventOpsProvider extends EventOpsDataProvider {
  constructor(initialEvents, initialDecisions) {
    super();
    this.events = JSON.parse(JSON.stringify(initialEvents || window.EVENTOPS_DEFAULT_EVENTS || []));
    this.decisions = JSON.parse(JSON.stringify(initialDecisions || window.EVENTOPS_DEFAULT_DECISIONS || []));
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
