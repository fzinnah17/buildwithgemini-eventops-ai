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

"""Event Visual Director powered by Gemini image generation and Cloud Storage."""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
import uuid

from google import genai
from google.cloud import storage

from app.event_store import get_event_store

logger = logging.getLogger(__name__)

MEDIA_BUCKET_NAME = "eventops-ai-media-qwiklabs-gcp-04-a69f0245a9b4"
PROJECT_ID = "qwiklabs-gcp-04-a69f0245a9b4"


def generate_event_visual(
    event_id: str,
    prompt_concept: str = "",
) -> str:
    """Generate an editorial spatial moodboard and visual concept for an event.

    Generates a high-fidelity editorial concept image using gemini-2.5-flash-image,
    saves the image artifact locally, uploads it to Google Cloud Storage with
    public read access, and registers the visual asset in the Event Dossier.

    Args:
        event_id: The unique event ID (e.g. 'evt_wit_manhattan_2026').
        prompt_concept: Optional visual prompt focus or stylistic nuance.

    Returns:
        JSON string containing the public HTTPS image URL, artifact path, and mood description.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})

    # Build refined editorial prompt adhering to aesthetic standards
    base_atmosphere = event.atmosphere or "warm, sophisticated, intimate candlelight dinner"
    concept_nuance = f"Focus on: {prompt_concept}." if prompt_concept else ""

    editorial_prompt = (
        f"Editorial interior architectural photograph of an elegant private dining room in Manhattan for an executive gathering. "
        f"Atmosphere: {base_atmosphere}. {concept_nuance} "
        f"Warm dimmable candlelight, seasonal minimalist bud vases and subtle botanical arrangements, "
        f"polished dark walnut dining table set with artisanal ceramic tableware and fine glassware, "
        f"textured linen napkins, understated elegant room acoustics. "
        f"Style: Architectural Digest editorial photography, Hasselblad medium format look, natural soft shadows, warm amber and midnight tones. "
        f"Composition: Beautiful empty room before guest arrival, serene and welcoming. "
        f"Strict negative constraints: Do NOT include any people, faces, human figures, cartoon styles, or visible text or letters anywhere in the image."
    )

    try:
        # Generate with Gemini image model
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=editorial_prompt,
        )

        image_bytes = None
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        break
            if image_bytes:
                break

        if not image_bytes:
            return json.dumps({
                "status": "error",
                "message": "Model generated a text response but did not return image data.",
            })

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        asset_id = f"vis_{uuid.uuid4().hex[:6]}"
        filename = f"{event_id}_{asset_id}_{timestamp_str}.png"

        # 1. Save locally as artifact
        artifact_dir = Path("/config/.gemini/antigravity/brain/05a062d3-beb6-414b-9777-4b7081661e78")
        if not artifact_dir.exists():
            artifact_dir = Path("./artifacts")
            artifact_dir.mkdir(parents=True, exist_ok=True)

        local_path = artifact_dir / filename
        with open(local_path, "wb") as f:
            f.write(image_bytes)

        # 2. Upload to Cloud Storage
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(MEDIA_BUCKET_NAME)
        gcs_blob_name = f"events/{event_id}/{filename}"
        blob = bucket.blob(gcs_blob_name)
        blob.upload_from_filename(str(local_path), content_type="image/png")

        public_url = f"https://storage.googleapis.com/{MEDIA_BUCKET_NAME}/{gcs_blob_name}"

        # 3. Register asset on event dossier
        visual_record = {
            "asset_id": asset_id,
            "filename": filename,
            "public_url": public_url,
            "local_path": str(local_path),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "concept_prompt": prompt_concept or base_atmosphere,
        }
        current_visuals = list(event.visual_assets or [])
        current_visuals.append(visual_record)
        store.update_event_fields(event_id, {"visual_assets": current_visuals})

        return json.dumps({
            "status": "success",
            "event_id": event_id,
            "asset_id": asset_id,
            "public_url": public_url,
            "local_path": str(local_path),
            "concept": prompt_concept or base_atmosphere,
            "message": "Generated editorial moodboard image and uploaded to Cloud Storage with public access.",
        }, indent=2)

    except Exception as e:
        logger.error("Visual generation failed: %s", e)
        return json.dumps({
            "status": "error",
            "message": f"Visual generation failed: {e}",
        })
