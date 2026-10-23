# app/main.py

from fastapi import FastAPI, HTTPException, status
from app.config import settings
from app.schemas import GatewayRequest, GatewayResponse, StructuredAnalysisResponse  # <--- Added StructuredAnalysisResponse
from app.guardrails.pii_sanitizer import PIISanitizer
from app.guardrails.injection_detector import InjectionDetector
from app.services.llm_service import LLMService
from app.evaluation.real_time_eval import EgressEvaluator

app = FastAPI(
    title=settings.APP_NAME,
    description="Deterministic local LLM inference gateway with automated evaluation."
)

llm_service = LLMService()
evaluator = EgressEvaluator(shared_model=llm_service.model)

@app.post("/api/v1/generate", response_model=GatewayResponse)
async def process_request(request: GatewayRequest):
    # 1. Ingress: Injection Check
    is_adversarial, reason = InjectionDetector.is_adversarial(request.query)
    if is_adversarial:
        return GatewayResponse(
            data=None,
            is_safe=False,
            passed_evaluation=False,
            faithfulness_score=0.0,
            blocked_reason=f"Request blocked by safety filter: {reason}"
        )

    # 2. Ingress: PII Sanitization
    sanitized_query, _ = PIISanitizer.sanitize(request.query)

    # 3. Model Inference (Pydantic Schema Validation)
    try:
        structured_output = llm_service.generate_grounded_response(
            clean_query=sanitized_query,
            context=request.retrieval_context
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failure: {str(e)}"
        )

    # 4. Egress: Factual Faithfulness Verification
    full_output = f"{structured_output.summary} " + " ".join(structured_output.key_points)

    passed_eval, faith_score = evaluator.evaluate_faithfulness(
        query=sanitized_query,
        context=request.retrieval_context,
        output_text=full_output
    )

    if not passed_eval:
        return GatewayResponse(
            data=StructuredAnalysisResponse(
                summary="Response suppressed by egress filter: Generated claims could not be verified against reference context.",
                key_points=["Factual grounding verification failed."],
                citations=[],
                confidence_score=0.0
            ),
            is_safe=True,
            passed_evaluation=False,
            faithfulness_score=faith_score,
            blocked_reason=(
                f"Evaluation Circuit Breaker Triggered: Faithfulness score ({faith_score:.2f}) "
                f"fell below required threshold ({settings.FAITHFULNESS_THRESHOLD})."
            )
        )

    return GatewayResponse(
        data=structured_output,
        is_safe=True,
        passed_evaluation=True,
        faithfulness_score=faith_score,
        blocked_reason=None
    )