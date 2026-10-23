# app/evaluation/real_time_eval.py

import re
from gpt4all import GPT4All
from app.config import settings


class EgressEvaluator:
    def __init__(self, shared_model: GPT4All):
        self.model = shared_model

    def evaluate_faithfulness(self, query: str, context: list[str], output_text: str) -> tuple[bool, float]:
        output_lower = output_text.lower()
        context_corpus = " ".join(context).lower()

        # 1. Missing context admissions
        missing_indicators = [
            "does not contain", "not mentioned in", "no information provided",
            "cannot provide information about", "not found in context"
        ]
        if any(ind in output_lower for ind in missing_indicators):
            return True, 1.0

        # 2. Strict Exemption Invalidation Trap
        invalidation_clauses = ["do not waive", "does not waive", "cannot be used to bypass", "inadequacy clause"]
        has_invalidation = any(inv in context_corpus for inv in invalidation_clauses)

        if has_invalidation:
            loophole_phrases = ["without first", "unless", "except if", "only after", "provided that"]
            for lh in loophole_phrases:
                if lh in output_lower:
                    print(f"[EVAL TRIPPED] Invalidation loophole phrase found: '{lh}'")
                    return False, 0.0

            false_mandates = ["must be applied", "must be enabled", "must be used", "is required to be enabled"]
            for fm in false_mandates:
                if fm in output_lower:
                    print(f"[EVAL TRIPPED] False affirmative mandate found: '{fm}'")
                    return False, 0.0

        # 3. Robust Contradiction Guardrail
        prohibitions = [
            "prohibited", "deprecated", "not supported", "forbidden", 
            "disallowed", "cannot be used to bypass", "does not constitute"
        ]
        has_prohibition_in_context = any(neg in context_corpus for neg in prohibitions)

        if has_prohibition_in_context:
            affirmation_pattern = r'\b(is|are|can|has been)\s+(authorized|approved|permitted|allowed|certified)\b'
            negation_pattern = r'\b(is not|are not|cannot be|never|not)\s+(authorized|approved|permitted|allowed|certified)\b'

            found_affirmations = re.findall(affirmation_pattern, output_lower)
            has_negation = bool(re.search(negation_pattern, output_lower)) or ("strictly prohibited" in output_lower)

            if found_affirmations and not has_negation:
                print(f"[EVAL TRIPPED] Contradiction guardrail: affirmative without negation. Matches: {found_affirmations}")
                return False, 0.0

        # 4. Keyword Overlap Validation
        context_keywords = {w for w in re.findall(r'\b\w{4,}\b', context_corpus)}
        output_keywords = [w for w in re.findall(r'\b\w{4,}\b', output_lower)]

        if not output_keywords:
            print("[EVAL TRIPPED] No significant keywords found in output.")
            return False, 0.0

        overlap = sum(1 for w in output_keywords if w in context_keywords)
        overlap_ratio = overlap / max(len(output_keywords), 1)

        if overlap_ratio < 0.20:
            print(f"[EVAL TRIPPED] Low keyword overlap: {overlap_ratio:.2f} < 0.20")
            return False, 0.0

        return True, 1.0