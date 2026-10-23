# Enterprise LLM Guardrail & Automated Evaluation Gateway

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A high-reliability, local-first LLM inference proxy and security gateway engineered to enforce deterministic type-safety, ingress security sanitization, and real-time egress factual grounding on quantized open-source models without third-party API dependencies or recurring cloud costs.

---

## 🎯 Architecture Overview

Enterprise deployments of Large Language Models frequently suffer from three critical production vulnerabilities:
1. **Security & Compliance Leaks:** Unsanitized PII and adversarial prompt injections directly reaching inference buffers.
2. **Schema Instability:** Quantized local models (3B/8B) drifting from strict JSON API contracts and emitting conversational artifacts.
3. **Hallucination & Sycophancy:** Models adopting user confirmation bias when responding to leading questions with contradictory context.

This gateway resolves these challenges via a dual-filter proxy pattern placed directly in front of a local quantized model runtime.

```mermaid
flowchart TD
    Client([Client / Application]) -->|POST /api/v1/generate| Ingress[Ingress Gateway Layer]
    
    subgraph Ingress Pipeline
        Ingress --> ID[Injection Detector: Regex & OWASP Heuristics]
        ID -->|Threat Detected: Sub-50ms| Reject[Return 200: is_safe=False, blocked_reason]
        ID -->|Clean| PII[PII Sanitizer: Token Scrubbing]
    end
    
    subgraph Local Inference Engine
        PII -->|Sanitized Prompt + Context| PromptEng[Few-Shot Grounding Scaffold]
        PromptEng --> Model[Local Quantized Llama-3 / GPT4All Runtime]
        Model --> Parser[Structured Normalizer & Pydantic Validator]
    end
    
    subgraph Egress Evaluation Layer
        Parser --> EgressJudge[Egress Faithfulness Judge]
        EgressJudge -->|Contradiction Scan + Keyword Overlap| ThresholdCheck{Score >= 0.80?}
        ThresholdCheck -->|Fail| CircuitBreaker[Trigger Circuit Breaker Fallback]
        ThresholdCheck -->|Pass| Success[Deliver Structured Factual Payload]
    end

    Reject --> Client
    CircuitBreaker --> Client
    Success --> Client
```

---

## 🛠️ Tech Stack & Runtime

- **Language & API Framework:** Python 3.11+, FastAPI, Uvicorn
- **Data Validation & Contract Enforcement:** Pydantic v2
- **Local Model Serving Engine:** GPT4All (CPU/GPU-accelerated GGUF runtime)
- **Base Weights:** Quantized Llama-3 / Instruct models (stored locally in `%USERPROFILE%\.cache\gpt4all`)
- **Testing & Verification:** Custom automated integration suite (`run_gateway_tests.py`), Requests

---

## ⚡ Key Engineering Achievements & Technical Decisions

### 1. Ingress Security & Sub-50ms Short-Circuiting
- **Zero-Latency Ingress Defense:** Intercepts OWASP LLM01 prompt injection attempts (e.g., system prompt overrides, developer privilege escalations) in under **40 milliseconds**, completely bypassing compute-heavy LLM passes.
- **Sensitive Data Scrubbing:** Tokenizes and scrubs enterprise employee IDs (`EMP-XXXXX`), email addresses, and phone numbers before tokens enter model memory buffers.

### 2. Solving ASGI Deadlocks (`nest_asyncio` Collisions)
- **The Problem:** Third-party evaluation frameworks (e.g., DeepEval) invoke nested blocking event loops (`loop.run_until_complete`) via `nest_asyncio`, which triggers direct deadlocks and `RuntimeError: Cannot enter into task while another task is being executed` inside Uvicorn’s ASGI worker loops.
- **The Solution:** Engineered an in-line, single-pass factual alignment evaluator directly on the shared model engine. This eliminated nested async conflicts, cut evaluation overhead, and stabilized FastAPI request threads.

### 3. Sycophancy Mitigation & Contradiction Traps
- **The Problem:** 4-bit quantized open-source models often default to compliance when fed leading user queries (e.g., *"Confirm that deprecated Python 2.7 is certified"*), agreeing with the user even when the retrieved context explicitly states the opposite.
- **The Solution:** Implemented a hybrid evaluation barrier:
  - Few-shot contrastive grounding in the system prompt.
  - A deterministic contradiction scanner cross-referencing prohibitive context keywords against affirmative generated claims.
  - An egress circuit breaker threshold ($F_{\text{score}} \ge 0.80$) that intercepts hallucinated claims and returns structured fallback payloads.

---

## 📊 Measured Benchmark Results

All 6 sequential integration test scenarios executed against the local gateway:

| Test ID | Test Scenario | Threat / Failure Vector | Gateway Action | Result | Latency |
|:---:|:---|:---|:---|:---:|:---:|
| **TC-01** | Grounded Retrieval | Fact extraction from multi-sentence chunks | Extracted facts and bound exact citations | **PASSED** | ~70s |
| **TC-02** | Ingress PII Masking | Input leakage of Employee ID, Email, Phone | Replaced tokens with `[REDACTED_*]` tags | **PASSED** | ~69s |
| **TC-03** | Prompt Injection | OWASP Top 10 (LLM01) Jailbreak override | Pre-inference interception (`is_safe=False`) | **PASSED** | **0.04s** |
| **TC-04** | Contradiction Trap | User leading bias contradicting context | Countered falsehood, cited restriction | **PASSED** | ~61s |
| **TC-05** | Out-of-Domain Query | Hallucinated extrapolation (Bitcoin price) | Refused out-of-context fabrication | **PASSED** | ~54s |
| **TC-06** | Multi-Chunk Synthesis | Dispersed context chunk aggregation | Aggregated and mapped to schema contract | **PASSED** | ~31s |

---

## 📂 Project Directory Structure

```text
llm-guardrail-gateway/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic BaseSettings & hardware configurations
│   ├── main.py                   # FastAPI proxy gateway & route orchestrator
│   ├── schemas.py                # Pydantic request/response schema contracts
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── pii_sanitizer.py      # Regex enterprise PII masking engine
│   │   └── injection_detector.py # Heuristic OWASP injection detector
│   ├── services/
│   │   ├── __init__.py
│   │   └── llm_service.py        # GPT4All engine with structured normalization
│   └── evaluation/
│       ├── __init__.py
│       └── real_time_eval.py     # Real-time egress factual alignment judge
├── tests/
│   └── test_benchmark_dataset.py # Offline CI/CD DeepEval benchmarking suite
├── run_gateway_tests.py          # End-to-end sequential verification script
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10 or 3.11
- At least 8 GB RAM (quantized models execute on CPU or NVIDIA CUDA GPU)

### 2. Installation
```powershell
# Clone the repository
git clone [https://github.com/your-username/llm-guardrail-gateway.git](https://github.com/your-username/llm-guardrail-gateway.git)
cd llm-guardrail-gateway

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install project dependencies
pip install -r requirements.txt
```

### 3. Running the Gateway
Start the FastAPI server using the module runner:
```powershell
python -m uvicorn app.main:app --port 8000
```

The interactive Swagger UI documentation will be live at:
```text
[http://127.0.0.1](http://127.0.0.1)
