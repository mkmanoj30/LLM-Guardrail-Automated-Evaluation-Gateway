from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# Ingress: Payload received by API
class GatewayRequest(BaseModel):
    query: str = Field(..., min_length=3, description="User question or operational query")
    retrieval_context: List[str] = Field(
        default=[], 
        description="Retrieved documentation/context chunks to ground the model"
    )

# Alias for backwards compatibility
QueryRequest = GatewayRequest

# Model Output: Structured schema the local model is forced to generate
class StructuredAnalysisResponse(BaseModel):
    summary: str = Field(..., description="A concise 2-3 sentence answer grounded solely in context")
    key_points: List[str] = Field(..., description="Bullet points summarizing factual context findings")
    citations: List[str] = Field(..., description="Direct verbatim quotes extracted from context")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model self-assessed confidence")

# Egress: Final payload returned to caller
class GatewayResponse(BaseModel):
    data: Optional[StructuredAnalysisResponse] = None
    is_safe: bool = True
    passed_evaluation: bool = True
    faithfulness_score: float
    blocked_reason: Optional[str] = None
    routing_metadata: Optional[Dict[str, Any]] = None