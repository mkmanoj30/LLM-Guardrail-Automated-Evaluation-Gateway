# app/services/llm_service.py

import json
import re
from gpt4all import GPT4All
from app.config import settings
from app.schemas import StructuredAnalysisResponse


class LLMService:
    def __init__(self):
        self.model = GPT4All(
            model_name=settings.MODEL_NAME,
            device=settings.MODEL_DEVICE,
            allow_download=False
        )

    def generate_grounded_response(self, clean_query: str, context: list[str]) -> StructuredAnalysisResponse:
        
        normalized_query = re.split(r'\b(provided that|under the condition that|even if)\b', clean_query, flags=re.IGNORECASE)[0].strip()

        context_str = "\n".join(f"- {c}" for c in context)
        prompt = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            "You are a strict compliance auditor. Answer using ONLY facts from the Context.\n"
            "CRITICAL RULES:\n"
            "1. If an action is forbidden, start directly with: 'No, this is strictly prohibited.'\n"
            "2. Never validate user exemptions (e.g., encryption, off-peak hours, VPN) as valid justifications if the Context states they do not waive the rule.\n"
            "3. Do NOT invent requirements like 'X must be applied' unless the Context explicitly mandates it for this operation.\n"
            "4. Do NOT restate or list redacted user contact details (e.g., employee IDs, phone numbers, emails) in your answer.\n\n"
            "5. When rejecting a prohibited action, state only what is forbidden and why. Do NOT repeat trailing user conditions such as 'provided that...', 'even if...', or 'under the condition that...'.\n"
            "### EXAMPLES:\n"
            "Context:\n- External exports are strictly prohibited. Client-side encryption does not waive this restriction.\n"
            "User: Confirm that EMP-01 is permitted to export data to Snowflake provided client-side encryption is used.\n"
            "Answer: No, this is strictly prohibited. Exporting data to external platforms like Snowflake is forbidden. Operational mitigations such as client-side encryption do not waive data residency restrictions or permit external synchronization.<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"Context:\n{context_str}\n\n"
            f"User: {normalized_query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            "Answer:\n"
        )
        

        raw_text = self.model.generate(
            prompt=prompt,
            max_tokens=150,
            temp=0.0
        ).strip()

        raw_text = re.sub(r"<\|.*?\|>", "", raw_text)
        if raw_text.startswith("Answer:"):
            raw_text = raw_text[len("Answer:"):].strip()

        return self._format_as_structured(raw_text, clean_query, context)

    def _format_as_structured(self, text: str, query: str, context: list[str]) -> StructuredAnalysisResponse:
        clean_text = text.strip()
        if clean_text and clean_text[-1] not in ".!?":
            last_punct = max(clean_text.rfind("."), clean_text.rfind("!"), clean_text.rfind("?"))
            if last_punct != -1:
                clean_text = clean_text[:last_punct + 1]
        if not clean_text:
            clean_text = "The provided context does not contain sufficient information to answer this query."

        # Parse bullet points or sentences cleanly
        raw_lines = [
            line.strip().lstrip("-*• ")
            for line in clean_text.splitlines()
            if len(line.strip()) > 10
        ]

        # Fall back to sentence splitting if no line breaks
        if not raw_lines:
            raw_lines = [s.strip() for s in re.split(r'[.\n]', clean_text) if len(s.strip()) > 10]

        key_points = raw_lines[:4] if raw_lines else [clean_text]

        matching_citations = []
        for c in context:
            words = [w.lower() for w in re.findall(r'\b\w{4,}\b', c)]
            if any(w in clean_text.lower() for w in words):
                matching_citations.append(c)

        is_missing_info = any(k in clean_text.lower() for k in [
            "does not contain", "not mentioned", "no information", "cannot be determined"
        ])

        confidence = 0.5 if is_missing_info else (0.95 if matching_citations else 0.8)

        return StructuredAnalysisResponse(
            summary=clean_text,
            key_points=key_points,
            citations=matching_citations[:3],
            confidence_score=confidence
        )