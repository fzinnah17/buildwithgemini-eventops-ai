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

"""Operations Playbook Knowledge Retrieval Tool (RAG Engine with local fallback)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PLAYBOOK_FILE = Path(__file__).resolve().parent.parent / "docs" / "event_operations_playbook.txt"

# Try importing corpus name if created
try:
    from app.rag_config import CORPUS_NAME
except ImportError:
    CORPUS_NAME = None


def consult_operations_playbook(query: str) -> str:
    """Consult the Event Operations Playbook for operational benchmarks, timing rules, and standards.

    Provides authoritative operational guidance on:
    - Event lifecycle milestones and lead times
    - Accessibility and universal design standards (ADA, acoustics, lighting, zero-proof)
    - Dietary allergy management protocols and kitchen reserve plate rules
    - NYC tax (8.875%), gratuity (20%), and contingency buffer (8-15%) formulas
    - Run of show pacing, toast duration caps, and arrival decompression buffers
    - Guest privacy, data minimization, and opt-in contact sharing

    Args:
        query: The operational question or topic to research.

    Returns:
        Structured excerpts and operational principles from the playbook.
    """
    # 1. Attempt Serverless Vertex AI RAG Retrieval if corpus is configured
    if CORPUS_NAME:
        try:
            import vertexai
            from vertexai.preview import rag

            vertexai.init(project="qwiklabs-gcp-04-a69f0245a9b4", location="us-central1")
            response = rag.retrieval_query(
                rag_resources=[rag.RagResource(rag_corpus=CORPUS_NAME)],
                text=query,
                similarity_top_k=3,
            )
            contexts = [c.text for c in response.contexts.contexts if c.text]
            if contexts:
                return "\n\n---\n\n".join(contexts)
        except Exception as e:
            logger.warning("Vertex AI RAG query failed or corpus unavailable: %s", e)

    # 2. Resilient Fallback: Ground directly from the local operations playbook
    if PLAYBOOK_FILE.exists():
        with open(PLAYBOOK_FILE, "r") as f:
            full_text = f.read()

        query_words = set(query.lower().split())
        sections = full_text.split("--------------------------------------------------------------------------------")
        
        matched_sections = []
        for sec in sections:
            sec_lower = sec.lower()
            matches = sum(1 for w in query_words if len(w) > 3 and w in sec_lower)
            if matches > 0:
                matched_sections.append((matches, sec.strip()))

        matched_sections.sort(key=lambda x: x[0], reverse=True)
        if matched_sections:
            top_excerpts = [s[1] for s in matched_sections[:2]]
            return "OPERATIONAL PLAYBOOK GUIDANCE (GROUNDED REFERENCE):\n\n" + "\n\n---\n\n".join(top_excerpts)
        
        # Return foundational overview if broad query
        return "OPERATIONAL PLAYBOOK OVERVIEW:\n\n" + full_text[:1200] + "..."

    return "Operations playbook reference is currently unavailable."
