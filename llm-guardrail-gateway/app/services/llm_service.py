# app/services/llm_service.py

import gc
from gpt4all import GPT4All
from app.config import settings
from app.services.router_service import ModelTier


class LLMService:
    def __init__(self):
        self._current_model: GPT4All | None = None
        self._current_model_name: str | None = None

    def _load_model(self, model_name: str) -> GPT4All:
        """Loads model into GPU VRAM, swapping cleanly if needed."""
        if self._current_model_name == model_name and self._current_model is not None:
            return self._current_model

        # Evict old model to maintain strict < 4GB VRAM utilization
        if self._current_model is not None:
            print(f"[VRAM MGR] Evicting {self._current_model_name} from GPU...")
            del self._current_model
            gc.collect()

        print(f"[VRAM MGR] Loading {model_name} into {settings.DEVICE}...")
        self._current_model = GPT4All(
            model_name=model_name,
            model_path=settings.MODEL_PATH or None,
            allow_download=True,
            device=settings.DEVICE,
            n_threads=settings.N_THREADS
        )
        self._current_model_name = model_name
        return self._current_model

    def generate(self, query: str, context: list[str], tier: ModelTier, max_tokens: int = 150) -> dict:
        target_file = settings.MODEL_TIER_1 if tier == ModelTier.TIER_1_LIGHT else settings.MODEL_TIER_2
        model = self._load_model(target_file)

        context_str = "\n".join(f"- {c}" for c in context) if context else "None"
        
        # 1. Tailor the prompt complexity to the model's capacity
        if tier == ModelTier.TIER_1_LIGHT:
            # Strict extraction format for 3B models to prevent numeric drift
            prompt = (
                f"### System:\nExtract the answer to the question using ONLY the provided context. "
                f"Do not modify, round, or hallucinate any numbers.\n\n"
                f"### Context:\n{context_str}\n\n"
                f"### User:\n{query}\n\n"
                f"### Response:\n"
            )
        else:
            # Strict compliance reasoning for 7B/8B models
            prompt = (
                f"You are a strict enterprise compliance validator.\n"
                f"Answer using ONLY facts from the Context block. If missing or unverified, state that clearly.\n\n"
                f"If the user query contradicts the context, explicitly deny it.\n\n"
                f"Context:\n{context_str}\n\n"
                f"User Query: {query}\n\n"
                f"Answer:"
            )

        with model.chat_session():
            raw_output = model.generate(prompt=prompt, max_tokens=max_tokens, temp=0.1)

        clean_text = raw_output.strip()
        if not clean_text:
            clean_text = "The provided context does not contain sufficient information to answer this query."

        # Detect admissions of missing context
        is_missing_info = any(k in clean_text.lower() for k in [
            "does not contain", "not mentioned", "no information", "cannot be determined"
        ])

        return {
            "summary": clean_text,
            "key_points": [clean_text],
            "citations": context if (context and not is_missing_info) else [],
            "confidence_score": 0.50 if is_missing_info else 0.95
        }

    def get_active_model_instance(self) -> GPT4All:
        """Returns the currently active GPT4All instance for egress evaluation."""
        if self._current_model is None:
            # Default fallback to Tier 1 on startup
            return self._load_model(settings.MODEL_TIER_1)
        return self._current_model