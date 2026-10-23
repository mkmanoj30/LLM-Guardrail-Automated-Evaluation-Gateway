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
```

    Reject --> Client
    CircuitBreaker --> Client
    Success --> Client
