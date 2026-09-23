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

"""Global pytest fixtures for EventOps AI test isolation and cloud-independent testing."""

import os
import pytest

# Enforce test environment flags by default
os.environ.setdefault("EVENTOPS_ENV", "test")
os.environ.setdefault("EVENTOPS_FORCE_DEMO", "true")
os.environ.setdefault("EVENTOPS_SIMULATED_INTEGRATIONS", "true")


@pytest.fixture(autouse=True)
def setup_test_store(monkeypatch):
    """Provide a clean, isolated in-memory event store for every test."""
    monkeypatch.setenv("EVENTOPS_ENV", "test")
    monkeypatch.setenv("EVENTOPS_FORCE_DEMO", "true")
    monkeypatch.setenv("EVENTOPS_SIMULATED_INTEGRATIONS", "true")

    from app.event_store import InMemoryEventStore, reset_event_store
    store = InMemoryEventStore()
    reset_event_store(store)
    yield store
    reset_event_store(None)
