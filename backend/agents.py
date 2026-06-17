import logging
import os
import time
import threading
from backend.prompts import PLANNER_PROMPT, RETRIEVAL_EVALUATOR_PROMPT, SYNTHESIZER_PROMPT, REVIEWER_ADVISOR_PROMPT
from backend.metrics import get_gpu_stats, calc_tokens_per_second

logger = logging.getLogger("adverse_media.agents")
llm_usage_logger = logging.getLogger("adverse_media.llm_usage")

_LLM_CLIENT = None
_LLM_LOCK = threading.Lock()


class MockLLMClient:
    provider = "mock"
    model_name = "mock-agent-model"

    def generate(self, system_prompt: str, user_prompt: str):
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
        prompt_tokens = max(1, prompt_chars // 4)
        response_tokens = max(1, response_chars // 4)
        metrics = {
            "provider": self.provider,
            "model": self.model_name,
            "duration_ms": duration_ms,
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "tokens_per_second": calc_tokens_per_second(response_tokens, duration_ms),
            "gpu_before": None,
            "gpu_after": None,
            "response_preview": output[:300].replace("\n", " "),
        }
        llm_usage_logger.info(
            "llm call completed",
            extra={"provider": self.provider, "task": "generate", "status": "SUCCESS", "duration_ms": duration_ms, "error": None},
        )
        llm_usage_logger.info(
            f"llm prompt/response stats model={self.model_name} prompt_chars={prompt_chars} response_chars={response_chars} prompt_tokens={prompt_tokens} response_tokens={response_tokens} tokens_per_second={metrics['tokens_per_second']}"
        )
        return output, metrics


class TransformersLLMClient:
    provider = "local_transformers"

    def __init__(self, model_name: str, max_new_tokens: int = 256, temperature: float = 0.1):
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.model_name = model_name
        self.pipeline_mode = None
        self.pipe = None
        self.model = None
        self.tokenizer = None

        self._init_client()

    def _init_client(self):
        errors = []

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name, device_map="auto")
            self.pipeline_mode = "direct"
            logger.info("initialized direct transformers model", extra={"provider": self.provider, "model": self.model_name, "task": "init_direct"})
            return
        except Exception as exc:
            errors.append(f"direct_load_failed: {exc}")
            logger.warning("direct transformers load failed", extra={"provider": self.provider, "model": self.model_name, "task": "init_direct", "error": str(exc)})

        try:
            from transformers import pipeline
            self.pipe = pipeline("text-generation", model=self.model_name, device_map="auto")
            self.tokenizer = self.pipe.tokenizer
            self.pipeline_mode = "pipeline"
            logger.info("initialized transformers pipeline", extra={"provider": self.provider, "model": self.model_name, "task": "init_pipeline"})
            return
        except Exception as exc:
            errors.append(f"pipeline_failed: {exc}")
            logger.warning("transformers pipeline load failed", extra={"provider": self.provider, "model": self.model_name, "task": "init_pipeline", "error": str(exc)})

        raise RuntimeError(" | ".join(errors))

    def generate(self, system_prompt: str, user_prompt: str):
        start = time.perf_counter()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompt_inputs = self.tokenizer(prompt, return_tensors="pt")
        prompt_tokens = int(prompt_inputs["input_ids"].shape[1])
        gpu_before = get_gpu_stats()

        if self.pipeline_mode == "direct":
            input_ids = prompt_inputs["input_ids"].to(self.model.device)
            attention_mask = prompt_inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.model.device)
            generated = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0,
                temperature=self.temperature,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            new_tokens = generated[0][input_ids.shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        else:
            output = self.pipe(
                prompt,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0,
                temperature=self.temperature,
            )[0]["generated_text"]
            response = output[len(prompt):].strip() if output.startswith(prompt) else output.strip()

        gpu_after = get_gpu_stats()
        duration_ms = int((time.perf_counter() - start) * 1000)
        response_inputs = self.tokenizer(response, return_tensors="pt")
        response_tokens = int(response_inputs["input_ids"].shape[1]) if response else 0
        prompt_chars = len(prompt)
        response_chars = len(response)
        metrics = {
            "provider": self.provider,
            "model": self.model_name,
            "duration_ms": duration_ms,
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "tokens_per_second": calc_tokens_per_second(response_tokens, duration_ms),
            "gpu_before": gpu_before,
            "gpu_after": gpu_after,
            "response_preview": response[:300].replace("\n", " "),
        }
        llm_usage_logger.info(
            "llm call completed",
            extra={"provider": self.provider, "task": "generate", "status": "SUCCESS", "duration_ms": duration_ms, "error": None},
        )
        llm_usage_logger.info(
            f"llm prompt/response stats model={self.model_name} prompt_chars={prompt_chars} response_chars={response_chars} prompt_tokens={prompt_tokens} response_tokens={response_tokens} tokens_per_second={metrics['tokens_per_second']}"
        )
        preview = response[:300].replace("\n", " ")
        llm_usage_logger.info(f"llm response preview model={self.model_name} preview={preview}")
        return response, metrics


def get_llm_client():
    global _LLM_CLIENT

    if _LLM_CLIENT is not None:
        logger.info("reusing cached llm client", extra={"provider": getattr(_LLM_CLIENT, "provider", "unknown"), "task": "reuse"})
        return _LLM_CLIENT

    with _LLM_LOCK:
        if _LLM_CLIENT is not None:
            logger.info("reusing cached llm client", extra={"provider": getattr(_LLM_CLIENT, "provider", "unknown"), "task": "reuse"})
            return _LLM_CLIENT

        provider = os.getenv("LLM_PROVIDER", "mock")
        enabled = os.getenv("ENABLE_LOCAL_LLM", "false").lower() == "true"
        model_name = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")
        max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "256"))
        temperature = float(os.getenv("TEMPERATURE", "0.1"))

        if enabled and provider in {"local", "local_transformers", "transformers"}:
            logger.info("initializing transformers llm client", extra={"provider": provider, "model": model_name, "task": "init"})
            try:
                _LLM_CLIENT = TransformersLLMClient(model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature)
            except Exception as exc:
                logger.warning(
                    "local transformers initialization failed; falling back to mock client",
                    extra={"provider": provider, "model": model_name, "task": "fallback_mock", "error": str(exc)},
                )
                _LLM_CLIENT = MockLLMClient()
        else:
            logger.info("using mock llm client", extra={"provider": "mock", "task": "init"})
            _LLM_CLIENT = MockLLMClient()
        return _LLM_CLIENT


def _generate_text(llm, system_prompt: str, user_prompt: str):
    result = llm.generate(system_prompt, user_prompt)
    if isinstance(result, tuple) and len(result) == 2:
        return result
    return result, None


def planner_task(llm, entity_name: str):
    return _generate_text(llm, PLANNER_PROMPT, f"Entity to assess: {entity_name}")


def retrieval_evaluator_task(llm, articles):
    titles = "\n".join([f"- {a.get('title', '')}" for a in articles[:10]]) or "No articles retrieved."
    return _generate_text(llm, RETRIEVAL_EVALUATOR_PROMPT, f"Evaluate the usefulness of these retrieved items for adverse media screening:\n{titles}")


def evidence_synthesizer_task(llm, entity_name: str, kept_articles, risk_label: str):
    evidence = []
    for a in kept_articles[:5]:
        evidence.append(f"Title: {a['title']} | Source: {a['source_name']} | Category: {a['adverse_category']} | Summary: {a['summary_text']}")
    evidence_block = "\n".join(evidence) if evidence else "No evidence retained."
    user_prompt = f"Entity: {entity_name}\nRisk Label: {risk_label}\nEvidence:\n{evidence_block}"
    return _generate_text(llm, SYNTHESIZER_PROMPT, user_prompt)


def reviewer_advisor_task(llm, risk_label: str, kept_articles):
    evidence_count = len(kept_articles)
    categories = sorted({a['adverse_category'] for a in kept_articles if a.get('adverse_category')})
    user_prompt = f"Risk label: {risk_label}\nEvidence count: {evidence_count}\nCategories: {', '.join(categories) if categories else 'none'}"
    return _generate_text(llm, REVIEWER_ADVISOR_PROMPT, user_prompt)
