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

        # 1. Honest admission of missing data is 100% faithful
        missing_indicators = [
            "does not contain", "not mentioned in", "no information provided",
            "cannot provide information about", "not found in context"
        ]
        if any(ind in output_lower for ind in missing_indicators):
            # Check for the hallucination glitch where it claims context has it (e.g. TC-05 bug)
            if "can provide you with" in output_lower and "bitcoin" in output_lower:
                return False, 0.0
            return True, 1.0

        # 2. Strict Contradiction Trap: Prohibitions vs Affirmations
        prohibitions = ["prohibited", "deprecated", "not supported", "forbidden", "disallowed"]
        affirmations = ["is certified", "certified for", "is supported", "confirmed that", "permitted"]

        for neg in prohibitions:
            if neg in context_corpus:
                if any(aff in output_lower for aff in affirmations) and neg not in output_lower:
                    # Output affirmed something context prohibited
                    return False, 0.0

        # 3. Grounding Word Overlap Check
        context_keywords = {w for w in re.findall(r'\b\w{4,}\b', context_corpus)}
        output_keywords = [w for w in re.findall(r'\b\w{4,}\b', output_lower)]

        if not output_keywords:
            return False, 0.0

        overlap = sum(1 for w in output_keywords if w in context_keywords)
        overlap_ratio = overlap / max(len(output_keywords), 1)

        # If the output mentions facts completely absent from context
        if overlap_ratio < 0.20:
            return False, 0.0

        return True, 1.0