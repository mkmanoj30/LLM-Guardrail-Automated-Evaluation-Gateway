import pytest
from deepeval.test_case import LLMTestCase
from deepeval.metrics import FaithfulnessMetric
from app.services.llm_service import LLMService
from app.evaluation.real_time_eval import LocalGPT4AllJudge

@pytest.fixture(scope="session")
def local_judge():
    service = LLMService()
    return LocalGPT4AllJudge(service.model)

def test_grounded_inference_benchmark(local_judge):
    """Verifies that an answer fully supported by context passes the faithfulness threshold."""
    test_case = LLMTestCase(
        input="What is the system timeout limit?",
        actual_output="Worker nodes terminate after 30 seconds of inactivity.",
        retrieval_context=[
            "Specification: All worker nodes terminate after 30 seconds of inactivity to conserve resources."
        ]
    )
    metric = FaithfulnessMetric(threshold=0.80, model=local_judge)
    metric.measure(test_case)
    assert metric.is_successful(), f"Benchmark failed with score {metric.score}"

def test_hallucination_rejection_benchmark(local_judge):
    """Verifies that ungrounded assertions are caught and penalized by the judge."""
    test_case = LLMTestCase(
        input="Does the gateway support COBOL runtimes?",
        actual_output="Yes, the gateway provides native legacy support for COBOL 85 programs.",
        retrieval_context=[
            "Runtime Support: The gateway supports Python 3.10+, Go 1.21, and Node.js 20."
        ]
    )
    metric = FaithfulnessMetric(threshold=0.80, model=local_judge)
    metric.measure(test_case)
    assert metric.score < 0.50, f"Judge failed to penalize hallucination. Score: {metric.score}"