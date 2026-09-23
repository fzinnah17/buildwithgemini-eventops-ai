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

"""EventOps AI enterprise integrations package."""

import os

from app.integrations.models import (
    IntegrationConnection,
    IntegrationAction,
    CalendarSyncEvent,
    EmailDraft,
    SlackMessagePayload,
    EventOpsTelemetryEvent,
)
from app.integrations.calendar import (
    CalendarProvider,
    GoogleCalendarProvider,
    DemoCalendarProvider,
)
from app.integrations.email import (
    EmailProvider,
    GmailProvider,
    DemoEmailProvider,
    validate_recipients,
)
from app.integrations.messaging import (
    MessagingProvider,
    SlackProvider,
    DemoMessagingProvider,
)
from app.integrations.analytics import (
    AnalyticsService,
    analytics_service,
)

__all__ = [
    "IntegrationConnection",
    "IntegrationAction",
    "CalendarSyncEvent",
    "EmailDraft",
    "SlackMessagePayload",
    "EventOpsTelemetryEvent",
    "CalendarProvider",
    "GoogleCalendarProvider",
    "DemoCalendarProvider",
    "EmailProvider",
    "GmailProvider",
    "DemoEmailProvider",
    "validate_recipients",
    "MessagingProvider",
    "SlackProvider",
    "DemoMessagingProvider",
    "AnalyticsService",
    "analytics_service",
    "get_calendar_provider",
    "get_email_provider",
    "get_messaging_provider",
]

_demo_calendar = DemoCalendarProvider()
_demo_email = DemoEmailProvider()
_demo_messaging = DemoMessagingProvider()

_real_calendar = GoogleCalendarProvider()
_real_email = GmailProvider()
_real_messaging = SlackProvider()


def is_simulation_enabled() -> bool:
    val = os.environ.get("EVENTOPS_SIMULATED_INTEGRATIONS")
    if val is not None:
        return val.lower() in ("true", "1", "yes")
    return True


def get_calendar_provider(force_demo: bool = False) -> CalendarProvider:
    if force_demo or os.environ.get("EVENTOPS_FORCE_DEMO", "").lower() in ("true", "1"):
        return _demo_calendar
    if is_simulation_enabled() and _real_calendar.get_connection_status().status != "connected":
        return _demo_calendar
    return _real_calendar


def get_email_provider(force_demo: bool = False) -> EmailProvider:
    if force_demo or os.environ.get("EVENTOPS_FORCE_DEMO", "").lower() in ("true", "1"):
        return _demo_email
    if is_simulation_enabled() and _real_email.get_connection_status().status != "connected":
        return _demo_email
    return _real_email


def get_messaging_provider(force_demo: bool = False) -> MessagingProvider:
    if force_demo or os.environ.get("EVENTOPS_FORCE_DEMO", "").lower() in ("true", "1"):
        return _demo_messaging
    if is_simulation_enabled() and _real_messaging.get_connection_status().status != "connected":
        return _demo_messaging
    return _real_messaging

