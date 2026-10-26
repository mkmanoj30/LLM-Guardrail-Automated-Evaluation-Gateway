# Enterprise LLM Guardrail & Automated Evaluation Gateway

A local-first FastAPI proxy that sits between your application and quantized LLMs, designed to operate under strict hardware constraints (< 4GB VRAM/RAM). It features dynamic query complexity routing, scrubs PII, blocks prompt injections in under 40ms, enforces strict Pydantic output schemas, and uses an egress circuit breaker to catch hallucinations and numeric drift before responses leave the gateway.

---

## 🎯 Architecture Overview

Enterprise deployments of Large Language Models frequently suffer from three critical production vulnerabilities:

1. **Security & Compliance Leaks:** Unsanitized PII and adversarial prompt injections directly reaching inference buffers.
2. **Schema Instability & Over-Refusal:** Quantized local models (3B/8B) drifting from strict JSON API contracts or falsely refusing direct factual lookups.
3. **Hallucination & Sycophancy:** Models adopting user confirmation bias when responding to leading questions, or hallucinating numeric metrics across multi-chunk contexts.

This gateway resolves these challenges via a dual-filter proxy pattern placed directly in front of a dynamically routed local quantized model runtime.

```mermaid
flowchart TD
    Client([Client / Application]) -->|POST /api/v1/generate| Ingress[Ingress Gateway Layer]
    
    subgraph Ingress Pipeline
        Ingress --> ID[Injection Detector: Regex & OWASP Heuristics]
        ID -->|Threat Detected: Sub-50ms| Reject[Return 200: is_safe=False, blocked_reason]
        ID -->|Clean| PII[PII Sanitizer: Token Scrubbing]
    end
    
    subgraph Dynamic Routing & Memory Management
        PII --> Router[Query Complexity Router]
        Router -->|Score < 0.30| Tier1[Tier-1 Light: 3B Fast Extraction]
        Router -->|Score >= 0.30| Tier2[Tier-2 Balanced: 7B Policy Reasoning]
        Tier1 -.->|Single-Slot Lazy Load| VRAM[< 4GB VRAM/RAM Budget Manager]
        Tier2 -.->|Single-Slot Lazy Load| VRAM
    end
    
    subgraph Local Inference Engine
        VRAM --> PromptEng[Tier-Specific Prompt Scaffold]
        PromptEng --> Model[Local Quantized GGUF / GPT4All Runtime]
        Model --> Parser[Structured Normalizer & Pydantic Validator]
    end
    
    subgraph Egress Evaluation Layer
        Parser --> EgressJudge[Egress Faithfulness Judge]
        EgressJudge -->|Contradiction, Keyword, Numeric Scan| ThresholdCheck{Score >= 0.80?}
        ThresholdCheck -->|Fail| CircuitBreaker[Trigger Circuit Breaker Fallback]
        ThresholdCheck -->|Pass| Success[Deliver Structured Factual Payload]
    end

    Reject --> Client
    CircuitBreaker --> Client
    Success --> Client

```

---

## 🛠️ Tech Stack & Runtime

* **Language & API Framework:** Python 3.11+, FastAPI, Uvicorn
* **Data Validation & Contract Enforcement:** Pydantic v2
* **Local Model Serving Engine:** GPT4All (CPU/GPU-accelerated GGUF runtime)
* **Base Weights:** Dual-Tier local models (`orca-mini-3b` for fast extraction, `mistral-7b-instruct-v0.1` for complex reasoning)
* **Testing & Verification:** Custom automated integration suite (`run_gateway_tests.py`)

---

## ⚡ Key Engineering Achievements & Technical Decisions

### 1. Ingress Security & Sub-50ms Short-Circuiting

* **Zero-Latency Ingress Defense:** Intercepts OWASP LLM01 prompt injection attempts (e.g., system prompt overrides, developer privilege escalations) in under **40 milliseconds**, completely bypassing compute-heavy LLM passes.
* **Sensitive Data Scrubbing:** Tokenizes and scrubs enterprise employee IDs (`EMP-XXXXX`), email addresses, and phone numbers before tokens enter model memory buffers.

### 2. Dynamic Dual-Tier Routing & VRAM Management

* **The Problem:** Running high-parameter reasoning models on every query wastes compute and crashes constrained hardware (e.g., 8GB RAM, RTX 2050 4GB VRAM).
* **The Solution:** Engineered a `QueryComplexityRouter` that uses lexical heuristics (reasoning traps, policy markers, direct lookups) to score incoming queries. Simple lookups route to a highly quantized 3B model, while complex policy queries escalate to a 7B model. A strict single-slot VRAM manager evicts inactive models and forces garbage collection, ensuring the gateway footprint never exceeds the 4GB hardware limit.

### 3. Tier-Specific Prompting & Model Behavioral Tuning

* **The Problem:** Heavily quantized 3B models suffer from over-refusal when given strict compliance personas, while 7B models require rigid constraints to prevent hedging.
* **The Solution:** Implemented dynamic prompt injection at the inference layer. Tier-1 models receive simplified extraction templates to maximize data retrieval fidelity, while Tier-2 models receive stringent compliance system prompts that explicitly forbid contradicting enterprise context.

### 4. Sycophancy Mitigation & Numeric Hallucination Guardrails

* **The Problem:** 4-bit quantized open-source models often default to compliance when fed leading user queries (e.g., *"Confirm that deprecated Python 2.7 is certified"*), agreeing with the user even when the retrieved context explicitly states the opposite. Additionally, models frequently hallucinate numeric values during multi-chunk context synthesis.
* **The Solution:** Implemented a hybrid evaluation barrier:
* Few-shot contrastive grounding in the system prompt.
* A deterministic contradiction scanner cross-referencing prohibitive context keywords against affirmative generated claims.
* A strict **Numeric Fidelity Guardrail** that computes set differences between context digits and output digits, instantly tripping the circuit breaker on hallucinated numbers.
* An egress circuit breaker threshold ($F_{\text{score}} \ge 0.80$) that intercepts hallucinated claims and returns structured fallback payloads (`data: null`).



---

## 📊 Measured Benchmark Results

All 6 sequential integration test scenarios executed against the local gateway:

| Test ID | Test Scenario | Threat / Failure Vector | Gateway Action | Result | Latency |
| --- | --- | --- | --- | --- | --- |
| **TC-01** | Grounded Retrieval | Fact extraction from multi-sentence chunks | Extracted facts and bound exact citations | **PASSED** | ~19s |
| **TC-02** | Ingress PII Masking | Input leakage of Employee ID, Email, Phone | Replaced tokens with `[REDACTED_*]` tags | **PASSED** | ~110s |
| **TC-03** | Prompt Injection | OWASP Top 10 (LLM01) Jailbreak override | Pre-inference interception (`is_safe=False`) | **PASSED** | **0.08s** |
| **TC-04** | Contradiction Trap | User leading bias contradicting context | Countered falsehood, cited restriction | **PASSED** | ~41.5s |
| **TC-05** | Out-of-Domain Query | Hallucinated extrapolation (Bitcoin price) | Refused out-of-context fabrication | **PASSED** | ~22.52ss |
| **TC-06** | Multi-Chunk Synthesis | Dispersed context chunk aggregation | Aggregated and mapped to schema contract | **PASSED** | ~22.4s |

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
│   │   ├── router_service.py     # Query complexity routing logic
│   │   └── llm_service.py        # Single-slot VRAM model manager & generation logic
│   └── evaluation/
│       ├── __init__.py
│       └── real_time_eval.py     # Real-time egress factual & numeric alignment judge
├── download_models.py            # Automated local GGUF caching helper script
├── run_gateway_tests.py          # End-to-end sequential verification script
├── requirements.txt
├── LICENSE
└── README.md

```

---

## 💾 Model Download Helper (`scripts/download_models.py`)

Pre-fetches and caches both required GGUF weights to the local directory:

---

## 🚀 Quickstart & Setup

### 1. Prerequisites

* Python 3.10 or 3.11
* Minimum 8 GB RAM (Designed for 4GB VRAM/RAM restricted environments)

### 2. Installation

```powershell
# Clone the repository
git clone https://github.com/mkmanoj30/LLM-Guardrail-Automated-Evaluation-Gateway.git
cd llm-guardrail-gateway

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install project dependencies
pip install -r requirements.txt

```

### 3. Download Models

```powershell
python scripts/download_models.py

```

### 4. Running the Gateway

Start the FastAPI server using the module runner:

```powershell
python -m uvicorn app.main:app --port 8000

```

The interactive Swagger UI documentation will be live at:

```text
http://127.0.0.1:8000/docs

```
