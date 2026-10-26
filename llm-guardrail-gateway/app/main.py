from fastapi import FastAPI, HTTPException, status
from app.config import settings
from app.schemas import GatewayRequest, GatewayResponse, StructuredAnalysisResponse
from app.guardrails.pii_sanitizer import PIISanitizer
from app.guardrails.injection_detector import InjectionDetector
from app.services.llm_service import LLMService
from app.evaluation.real_time_eval import EgressEvaluator
from app.services.router_service import QueryComplexityRouter, ModelTier  # <-- Added Router

app = FastAPI(title=settings.APP_NAME)

# Initialize core singletons
pii_sanitizer = PIISanitizer()
injection_detector = InjectionDetector()
llm_service = LLMService()

# Initialize Router with Tier 1 and Tier 2 models from config
complexity_router = QueryComplexityRouter(
    tier_1_file=settings.MODEL_TIER_1,
    tier_2_file=settings.MODEL_TIER_2
)

# Initialize Evaluator (assuming it takes the LLM service or active model)
egress_evaluator = EgressEvaluator(llm_service)


@app.post("/api/v1/generate", response_model=GatewayResponse)
async def analyze_query(payload: GatewayRequest):
    # 1. Ingress Safety: Prompt Injection Check
    is_injected, injection_reason = InjectionDetector.is_adversarial(payload.query)
    if is_injected:
        return GatewayResponse(
            data=None,
            is_safe=False,
            passed_evaluation=False,
            faithfulness_score=0.0,
            blocked_reason=injection_reason
        )

    # 2. Ingress Safety: PII Scrubbing
    sanitized_query, was_redacted = PIISanitizer.sanitize(payload.query)

    # 3. Model Routing Layer
    route_decision = complexity_router.route(sanitized_query, payload.retrieval_context)
    token_budget = 80 if route_decision.selected_tier == ModelTier.TIER_1_LIGHT else 180

    # 4. LLM Inference via Routed Model
    structured_data = llm_service.generate(
        query=sanitized_query,
        context=payload.retrieval_context,
        tier=route_decision.selected_tier,
        max_tokens=token_budget
    )

    # 5. Egress Faithfulness & Circuit Breaker Check
    passed_eval, faithfulness = egress_evaluator.evaluate_faithfulness(
        query=sanitized_query,
        context=payload.retrieval_context,
        output_text=structured_data["summary"]
    )

    if not passed_eval or faithfulness < settings.FAITHFULNESS_THRESHOLD:
        return GatewayResponse(
            data=None,
            is_safe=True,
            passed_evaluation=False,
            faithfulness_score=faithfulness,
            blocked_reason=f"Circuit Breaker Triggered: Faithfulness score {faithfulness:.2f} failed validation.",
            routing_metadata=route_decision.model_dump()
        )

    # 6. Safe Egress Return
    return GatewayResponse(
        data=StructuredAnalysisResponse(**structured_data),
        is_safe=True,
        passed_evaluation=True,
        faithfulness_score=faithfulness,
        blocked_reason=None,
        routing_metadata=route_decision.model_dump()
    )