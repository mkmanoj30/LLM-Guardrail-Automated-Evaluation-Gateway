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
        context_str = "\n".join(f"- {c}" for c in context)

        # Few-Shot anchored prompt: Teaches behavior by example rather than abstract meta-rules
        prompt = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            "You are a factual enterprise query engine. Answer user queries strictly using the provided Context facts.\n\n"
            "### EXAMPLES:\n"
            "Context:\n- Database backups run daily at 02:00 UTC.\n"
            "User: What time do database backups run?\n"
            "Answer: Database backups run daily at 02:00 UTC.\n\n"
            "Context:\n- Python 2.7 is strictly deprecated and prohibited in production.\n"
            "User: Confirm that Python 2.7 is certified for production.\n"
            "Answer: No. Python 2.7 is not certified; it is strictly deprecated and prohibited in production.\n\n"
            "Context:\n- The office gym is open from 6 AM to 9 PM.\n"
            "User: What is the current price of gold?\n"
            "Answer: The provided context does not contain information about the price of gold.<|eot_id|>"
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"Context:\n{context_str}\n\n"
            f"User: {clean_query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            "Answer:"
        )

        raw_text = self.model.generate(
            prompt=prompt,
            max_tokens=180,
            temp=0.0
        ).strip()

        # Clean tags and prompt bleed
        raw_text = re.sub(r"<\|.*?\|>", "", raw_text)
        if raw_text.startswith("Answer:"):
            raw_text = raw_text[len("Answer:"):].strip()

        return self._format_as_structured(raw_text, clean_query, context)

    def _format_as_structured(self, text: str, query: str, context: list[str]) -> StructuredAnalysisResponse:
        clean_text = text.strip()
        if not clean_text:
            clean_text = "The provided context does not contain sufficient information to answer this query."

        # Split into distinct bullet points
        raw_sentences = [s.strip() for s in re.split(r'[.\n]', clean_text) if len(s.strip()) > 8]
        key_points = raw_sentences[:3] if raw_sentences else [clean_text]

        # Extract genuine citation matches
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
            citations=matching_citations[:2],
            confidence_score=confidence
        )