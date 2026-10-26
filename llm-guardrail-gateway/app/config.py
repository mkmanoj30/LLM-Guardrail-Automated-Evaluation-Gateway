# app/config.py

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise LLM Guardrail & Intelligent Routing Gateway"
    DEBUG: bool = False

    # Models constrained under ~2-4 GB footprint
    # Tier 1: ~1.98 GB (Q4_0 quantized 3B model)
    MODEL_TIER_1: str = os.getenv("MODEL_TIER_1", "orca-mini-3b-gguf2-q4_0.gguf")
    
    # Tier 2: ~3.80 GB (Q4_0 quantized 7B/8B instruction model)
    MODEL_TIER_2: str = os.getenv("MODEL_TIER_2", "mistral-7b-instruct-v0.1.Q4_0.gguf")

    # Local storage path for GGUFs (defaults to ~/.cache/gpt4all if unset)
    MODEL_PATH: str = os.getenv("MODEL_PATH", "")

    # Hardware acceleration
    DEVICE: str = os.getenv("DEVICE", "cpu")  # 'gpu' or 'cpu'
    N_THREADS: int = int(os.getenv("N_THREADS", "4"))

    # Evaluation Threshold
    FAITHFULNESS_THRESHOLD: float = 0.80

    class Config:
        env_file = ".env"


settings = Settings()