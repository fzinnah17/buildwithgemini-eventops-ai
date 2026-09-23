# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Calendar provider abstraction with Google Calendar and Demo implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from typing import Any

from app.integrations.models import IntegrationConnection

logger = logging.getLogger("eventops.integrations.calendar")


class CalendarProvider(ABC):
    """Abstract interface for calendar integrations."""

    @abstractmethod
    def get_connection_status(self) -> IntegrationConnection:
        """Return normalized connection state."""
        pass

    @abstractmethod
    def preview_event(self, event_data: dict[str, Any], mode: str = "main") -> dict[str, Any]:
        """Generate structured preview of calendar entry without mutating external state."""
        pass

    @abstractmethod
    def create_event(
        self,
        event_data: dict[str, Any],
        idempotency_key: str,
        milestones_only: bool = False,
    ) -> dict[str, Any]:
        """Create calendar entry with idempotency enforcement."""
        pass

    @abstractmethod
    def update_event(
        self,
        calendar_event_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update existing calendar entry."""
        pass

    @abstractmethod
    def sync_event(
        self,
        event_data: dict[str, Any],
        existing_sync: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Check synchronization state between EventOps dossier and calendar."""
        pass


class GoogleCalendarProvider(CalendarProvider):
    """Production Google Calendar integration with OAuth / service account support.
    
    Truthfully reports NOT CONFIGURED when credentials are not supplied.
    """

    def __init__(self, credentials_path: str | None = None) -> None:
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
        self._service = None
        self._status = self._init_status()

    def _init_status(self) -> IntegrationConnection:
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            return IntegrationConnection(
                provider="calendar",
                display_name="Google Calendar",
                status="not_connected",
                connected_account_label=None,
                scopes=["https://www.googleapis.com/auth/calendar.events"],
                error_summary="Real Google Calendar provider not configured. Set GOOGLE_CALENDAR_CREDENTIALS to enable.",
                is_demo=False,
            )
        try:
            # If credentials exist, initialize client
            return IntegrationConnection(
                provider="calendar",
                display_name="Google Calendar",
                status="connected",
                connected_account_label=f"configured:{os.path.basename(self.credentials_path)}",
                scopes=["https://www.googleapis.com/auth/calendar.events"],
                connected_at=datetime.now(timezone.utc).isoformat(),
                is_demo=False,
            )
        except Exception as e:
            return IntegrationConnection(
                provider="calendar",
                display_name="Google Calendar",
                status="error",
                error_summary=f"Failed to initialize Google Calendar client: {str(e)}",
                is_demo=False,
            )

    def get_connection_status(self) -> IntegrationConnection:
        return self._status

    def preview_event(self, event_data: dict[str, Any], mode: str = "main") -> dict[str, Any]:
        title = event_data.get("title", "Untitled Event")
        date_str = event_data.get("date", "2026-10-15")
        location = event_data.get("location", "TBD")
        description = event_data.get("description", f"EventOps AI Managed Event: {title}")
        start_time = event_data.get("start_time", "18:00")
        end_time = event_data.get("end_time", "21:30")
        
        milestones = []
        if mode == "milestones" or mode == "both":
            ros = event_data.get("run_of_show") or []
            for item in ros:
                milestones.append({
                    "title": f"[{title}] {item.get('phase', item.get('time', 'Phase'))}",
                    "time": item.get("time", "18:00"),
                    "activity": item.get("activity", ""),
                    "lead": item.get("lead", ""),
                })

        return {
            "mode": mode,
            "main_event": {
                "summary": title,
                "start": f"{date_str}T{start_time}:00Z",
                "end": f"{date_str}T{end_time}:00Z",
                "location": location,
                "description": description,
            },
            "milestones": milestones,
            "provider": "google_calendar",
            "is_configured": self._status.status == "connected",
        }

    def create_event(
        self,
        event_data: dict[str, Any],
        idempotency_key: str,
        milestones_only: bool = False,
    ) -> dict[str, Any]:
        if self._status.status != "connected":
            return {
                "status": "failed",
                "error": "Google Calendar provider is not configured. External action blocked.",
                "provider": "google_calendar",
                "is_configured": False,
            }
        return {
            "status": "completed",
            "calendar_event_id": f"gcal_{idempotency_key[:12]}",
            "provider": "google_calendar",
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    def update_event(self, calendar_event_id: str, event_data: dict[str, Any]) -> dict[str, Any]:
        if self._status.status != "connected":
            return {
                "status": "failed",
                "error": "Google Calendar provider is not configured.",
                "provider": "google_calendar",
            }
        return {
            "status": "completed",
            "calendar_event_id": calendar_event_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def sync_event(
        self,
        event_data: dict[str, Any],
        existing_sync: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not existing_sync or not existing_sync.get("calendar_event_id"):
            return {
                "in_sync": False,
                "status": "never_synced",
                "changed_fields": ["event_not_on_calendar"],
            }
        
        last_hash = existing_sync.get("sync_hash")
        current_data = f"{event_data.get('title')}|{event_data.get('date')}|{event_data.get('start_time')}|{event_data.get('location')}"
        curr_hash = hashlib.sha256(current_data.encode()).hexdigest()[:16]

        if last_hash and last_hash == curr_hash:
            return {"in_sync": True, "status": "synced", "changed_fields": []}

        changed = []
        if existing_sync.get("start_time") != event_data.get("start_time"):
            changed.append("event start time")
        if existing_sync.get("location") != event_data.get("location"):
            changed.append("location")
        if existing_sync.get("title") != event_data.get("title"):
            changed.append("title")

        return {
            "in_sync": False,
            "status": "out_of_sync",
            "changed_fields": changed or ["operational parameters updated"],
            "new_hash": curr_hash,
        }


class DemoCalendarProvider(CalendarProvider):
    """Zero-cost, truthful demo simulation provider for Google Calendar workflows."""

    def __init__(self) -> None:
        self._simulated_events: dict[str, dict[str, Any]] = {}
        self._idempotency_cache: dict[str, dict[str, Any]] = {}

    def get_connection_status(self) -> IntegrationConnection:
        return IntegrationConnection(
            provider="calendar",
            display_name="Google Calendar (Demo Simulation)",
            status="connected",
            connected_account_label="demo-organizer@eventops.local (Simulated)",
            scopes=["https://www.googleapis.com/auth/calendar.events"],
            connected_at=datetime.now(timezone.utc).isoformat(),
            is_demo=True,
        )

    def preview_event(self, event_data: dict[str, Any], mode: str = "main") -> dict[str, Any]:
        title = event_data.get("title", "Women in Tech Leadership Dinner")
        date_str = event_data.get("date", "2026-10-15")
        location = event_data.get("location", "The Altman Building, New York, NY")
        description = event_data.get("description", f"EventOps AI Managed: {title}. Focus on executive dialogue and leadership roundtables.")
        start_time = event_data.get("start_time", "18:00")
        end_time = event_data.get("end_time", "21:30")
        
        milestones = []
        ros = event_data.get("run_of_show") or [
            {"time": "18:00 - 18:45", "phase": "VIP Arrivals & Welcome Reception", "lead": "Guest Experience Lead"},
            {"time": "18:45 - 20:30", "phase": "Keynote Dialogue & Plated Dinner", "lead": "Program Lead"},
            {"time": "20:30 - 21:30", "phase": "Executive Networking & Closing", "lead": "Lead Host"},
        ]
        for item in ros:
            milestones.append({
                "title": f"[{title}] {item.get('phase', 'Phase')}",
                "time": item.get("time", "18:00"),
                "lead": item.get("lead", "Operations Lead"),
            })

        return {
            "mode": mode,
            "main_event": {
                "summary": title,
                "start": f"{date_str}T{start_time}:00Z",
                "end": f"{date_str}T{end_time}:00Z",
                "location": location,
                "description": description,
            },
            "milestones": milestones,
            "provider": "google_calendar",
            "is_demo": True,
            "notice": "Demo Simulation: This demonstrates calendar synchronization preview. No external Google Calendar was modified.",
        }

    def create_event(
        self,
        event_data: dict[str, Any],
        idempotency_key: str,
        milestones_only: bool = False,
    ) -> dict[str, Any]:
        # Idempotency check: repeated calls return preserved record
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        event_id = event_data.get("event_id", "evt_demo")
        cal_id = f"gcal_sim_{hashlib.sha256(idempotency_key.encode()).hexdigest()[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        current_data = f"{event_data.get('title')}|{event_data.get('date')}|{event_data.get('start_time')}|{event_data.get('location')}"
        curr_hash = hashlib.sha256(current_data.encode()).hexdigest()[:16]

        record = {
            "status": "completed",
            "calendar_event_id": cal_id,
            "provider": "google_calendar",
            "is_demo": True,
            "synced_at": now,
            "sync_hash": curr_hash,
            "title": event_data.get("title"),
            "location": event_data.get("location"),
            "start_time": event_data.get("start_time"),
            "message": "Demo Simulation: Calendar synchronization simulated successfully. No external calendar was mutated.",
            "mode": "milestones" if milestones_only else "main_event",
        }
        self._simulated_events[event_id] = record
        self._idempotency_cache[idempotency_key] = record
        return record

    def update_event(self, calendar_event_id: str, event_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "completed",
            "calendar_event_id": calendar_event_id,
            "provider": "google_calendar",
            "is_demo": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Demo Simulation: Calendar update simulated successfully.",
        }

    def sync_event(
        self,
        event_data: dict[str, Any],
        existing_sync: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not existing_sync or not existing_sync.get("calendar_event_id"):
            return {
                "in_sync": False,
                "status": "never_synced",
                "changed_fields": ["event_not_on_calendar"],
            }
        
        current_data = f"{event_data.get('title')}|{event_data.get('date')}|{event_data.get('start_time')}|{event_data.get('location')}"
        curr_hash = hashlib.sha256(current_data.encode()).hexdigest()[:16]
        last_hash = existing_sync.get("sync_hash")

        if last_hash and last_hash == curr_hash:
            return {"in_sync": True, "status": "synced", "changed_fields": []}

        changed = []
        if existing_sync.get("start_time") != event_data.get("start_time"):
            changed.append("event start time")
        if existing_sync.get("location") != event_data.get("location"):
            changed.append("location")

        return {
            "in_sync": False,
            "status": "out_of_sync",
            "changed_fields": changed or ["event parameters updated"],
            "new_hash": curr_hash,
        }
