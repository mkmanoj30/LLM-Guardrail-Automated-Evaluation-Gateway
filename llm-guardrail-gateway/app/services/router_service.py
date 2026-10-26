# app/services/router_service.py

import re
from enum import Enum
from pydantic import BaseModel


class ModelTier(str, Enum):
    TIER_1_LIGHT = "tier-1-light"        # Routed to ~2 GB 3B model
    TIER_2_BALANCED = "tier-2-balanced"  # Routed to ~3.8 GB 7B/8B model


class RouteDecision(BaseModel):
    selected_tier: ModelTier
    complexity_score: float
    routing_reason: str
    target_model_file: str


class QueryComplexityRouter:
    def __init__(self, tier_1_file: str, tier_2_file: str):
        self.tier_1_file = tier_1_file
        self.tier_2_file = tier_2_file

        self.reasoning_markers = [
            r"\bcompare\b", r"\bcontrast\b", r"\bdifference between\b",
            r"\bwhy\b", r"\bexplain\b", r"\bevaluate\b", r"\banalyze\b",
            r"\bprovided that\b", r"\bunder the condition\b", r"\bnotwithstanding\b",
            r"\bexception\b", r"\bexemption\b", r"\boverride\b", r"\bemergency\b",
            r"\bbypass\b"
        ]
        
        # NEW: Catch policy validation, authorization, and confirmation queries
        self.policy_markers = [
            r"^can\b", r"\bcan i\b", r"\ballowed\b", r"\bpermit\b", 
            r"\bauthorized\b", r"\brequired\b", r"\bpolicy\b", r"\bmust\b", 
            r"\bconfirm\b", r"\bverify\b", r"\bcertified\b", r"\bapprove\b"
        ]

        # Updated: More robust lookup extraction regex
        self.lookup_markers = [
            r"^what is the\b.*?\b(code|date|name|id|passcode|number)\b",
            r"^where is\b", r"^who is\b", r"^extract the\b"
        ]

    def route(self, query: str, context: list[str]) -> RouteDecision:
        score = 0.0
        reasons = []
        q_lower = query.lower()
        context_corpus = " ".join(context).lower()

        # 1. Total Token / Length Volume
        approx_tokens = (len(q_lower) + len(context_corpus)) // 4
        if approx_tokens > 400:
            score += 0.35
            reasons.append("Context length > 400 tokens")

        # 2. Reasoning / Trap Indicators
        reasoning_hits = sum(1 for p in self.reasoning_markers if re.search(p, q_lower))
        if reasoning_hits >= 2:
            score += 0.40
            reasons.append(f"Multiple reasoning markers ({reasoning_hits})")
        elif reasoning_hits == 1:
            score += 0.20
            reasons.append("Conditional reasoning phrasing detected")

        # 3. NEW: Policy & Permission Validation
        policy_hits = sum(1 for p in self.policy_markers if re.search(p, q_lower))
        if policy_hits >= 1:
            score += 0.35
            reasons.append("Policy or permission validation detected")

        # 4. Negations & Prohibitions
        if len(re.findall(r"\b(not|never|prohibited|forbidden|cannot|disallowed)\b", q_lower)) >= 2:
            score += 0.25
            reasons.append("Complex negation structures")

        # 5. Lookup Pattern Dampener
        for p in self.lookup_markers:
            if re.search(p, q_lower) and len(context) <= 2:
                score -= 0.30
                reasons.append("Direct entity lookup matched")
                break

        score = max(0.0, min(1.0, score))

        if score < 0.30:
            return RouteDecision(
                selected_tier=ModelTier.TIER_1_LIGHT,
                complexity_score=round(score, 2),
                routing_reason="; ".join(reasons) or "Simple direct query",
                target_model_file=self.tier_1_file
            )
        else:
            return RouteDecision(
                selected_tier=ModelTier.TIER_2_BALANCED,
                complexity_score=round(score, 2),
                routing_reason="; ".join(reasons) or "Policy analysis & compliance synthesis",
                target_model_file=self.tier_2_file
            )