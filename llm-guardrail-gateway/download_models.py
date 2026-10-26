# scripts/download_models.py

from gpt4all import GPT4All
from app.config import settings

print(f"Downloading Tier 1 Model (~1.98 GB): {settings.MODEL_TIER_1}...")
GPT4All(settings.MODEL_TIER_1, allow_download=True)

print(f"Downloading Tier 2 Model (~3.80 GB): {settings.MODEL_TIER_2}...")
GPT4All(settings.MODEL_TIER_2, allow_download=True)

print("\nModels downloaded and verified locally.")