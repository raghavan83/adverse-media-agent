import logging
import os
import time
from backend.prompts import PLANNER_PROMPT, RETRIEVAL_EVALUATOR_PROMPT, SYNTHESIZER_PROMPT, REVIEWER_ADVISOR_PROMPT

logger = logging.getLogger("adverse_media.agents")
llm_usage_logger = logging.getLogger("adverse_media.llm_usage")

class MockLLMClient:
    provider = "mock"
    model_name = "mock-agent-model"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        start = time.perf_counter()
        if "planner agent" in system_prompt.lower():
            output = "Plan: retrieve news, validate entity match, filter adverse evidence, synthesize grounded findings, and recommend reviewer action."
        elif "retrieval evaluator" in system_prompt.lower():
            output = "The retrieved set appears useful for screening because it contains entity-relevant titles that can be scored for adverse relevance. Human validation is still required for ambiguous names."
        elif "evidence synthesizer" in system_prompt.lower():
            output = "Grounded summary: The retained articles indicate potentially adverse signals linked to the target entity. Reviewer should validate source context before a final decision."
        elif "reviewer advisor" in system_prompt.lower():
            output = "ESCALATE: multiple relevant adverse signals were retained for analyst review."
        else:
            output = "LLM task completed."
        duration_ms = int((time.perf_counter() - start) * 1000)
        prompt_chars = len(system_prompt) + len(user_prompt)
        response_chars = len(output)
        llm_usage_logger.info(
            "llm call completed",
            extra={
                "provider": self.provider,
                "task": "generate",
                "status": "SUCCESS",
                "duration_ms": duration_ms,
                "error": None,
            },
        )
        llm_usage_logger.info(
            f"llm prompt/response stats model={self.model_name} prompt_chars={prompt_chars} response_chars={response_chars}"
        )
        return output

class TransformersLLMClient:
    provider = "local_transformers"

    def __init__(self, model_name: str, max_new_tokens: int = 256, temperature: float = 0.1):
        from transformers import pipeline
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.model_name = model_name
        self.pipe = pipeline("text-generation", model=model_name, device_map="auto")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        start = time.perf_counter()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt = self.pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        output = self.pipe(prompt, max_new_tokens=self.max_new_tokens, do_sample=self.temperature > 0, temperature=self.temperature)[0]["generated_text"]
        response = output[len(prompt):].strip() if output.startswith(prompt) else output.strip()
        duration_ms = int((time.perf_counter() - start) * 1000)
        prompt_chars = len(prompt)
        response_chars = len(response)
        prompt_tokens_est = max(1, prompt_chars // 4)
        response_tokens_est = max(1, response_chars // 4)
        llm_usage_logger.info(
            "llm call completed",
            extra={
                "provider": self.provider,
                "task": "generate",
                "status": "SUCCESS",
                "duration_ms": duration_ms,
                "error": None,
            },
        )
        llm_usage_logger.info(
            f"llm prompt/response stats model={self.model_name} prompt_chars={prompt_chars} response_chars={response_chars} prompt_tokens_est={prompt_tokens_est} response_tokens_est={response_tokens_est}"
        )
        preview = response[:300].replace("\n", " ")
        llm_usage_logger.info(f"llm response preview model={self.model_name} preview={preview}")
        return response


def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "mock")
    enabled = os.getenv("ENABLE_LOCAL_LLM", "false").lower() == "true"
    model_name = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")
    max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "256"))
    temperature = float(os.getenv("TEMPERATURE", "0.1"))
    logger.info("initializing llm client", extra={"provider": provider, "task": "init"})
    if enabled:
        try:
            return TransformersLLMClient(model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature)
        except Exception as exc:
            logger.exception("local llm initialization failed; falling back to mock client", extra={"provider": "local_transformers", "task": "init", "status": "FAILED", "error": str(exc)})
            return MockLLMClient()
    return MockLLMClient()


def planner_task(llm, entity_name: str):
    return llm.generate(PLANNER_PROMPT, f"Target entity: {entity_name}")


def retrieval_evaluator_task(llm, articles: list[dict]):
    sample = "\n".join([a.get("title", "") for a in articles[:5]])
    return llm.generate(RETRIEVAL_EVALUATOR_PROMPT, f"Retrieved titles:\n{sample}")


def evidence_synthesizer_task(llm, entity_name: str, kept_articles: list[dict], risk_label: str):
    bullet_text = "\n".join([f"- {a['title']} | {a['source_name']} | {a['adverse_category']}" for a in kept_articles[:5]])
    return llm.generate(SYNTHESIZER_PROMPT, f"Entity: {entity_name}\nRisk label: {risk_label}\nEvidence:\n{bullet_text}")


def reviewer_advisor_task(llm, risk_label: str, kept_articles: list[dict]):
    count = len(kept_articles)
    return llm.generate(REVIEWER_ADVISOR_PROMPT, f"Risk label: {risk_label}\nEvidence count: {count}")
