from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Local Llama Guardrail & Evaluation Gateway"
    API_PORT: int = 8000
    
    # Model Selection: Llama-3-8B-Instruct or Llama-3.2-3B-Instruct for faster CPU execution
    MODEL_NAME: str = "orca-mini-3b-gguf2-q4_0.gguf"
    MODEL_DEVICE: str = "gpu"  # Options: "cpu", "gpu", or "kompute"
    
    # Reliability & Quality Thresholds
    FAITHFULNESS_THRESHOLD: float = 0.80
    MAX_RETRIES: int = 2

    class Config:
        env_file = ".env"

settings = Settings()