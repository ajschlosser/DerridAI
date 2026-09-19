from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from utils.strip_code_fence import strip_code_fence

LOG = logging.getLogger(__name__)

MAX_CONCURRENT_GENERATIONS = int(os.getenv("DERRIDAI_MAX_CONCURRENT_GENERATIONS", "1"))
DEFAULT_CHAT_MODEL = os.getenv("DERRIDAI_DEFAULT_CHAT_MODEL", "gemma4:e2b")
DEFAULT_CHAT_TEMPERATURE = float(os.getenv("DERRIDAI_DEFAULT_CHAT_TEMPERATURE", "0.0"))
DEFAULT_CHAT_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_REASONING = os.getenv("DERRIDAI_DEFAULT_REASONING", "0").lower() in {"1", "true", "yes"}
DEFAULT_NUM_CTX = int(os.getenv("DERRIDAI_DEFAULT_NUM_CTX", "26214"))
DEFAULT_MIROSTAT = int(os.getenv("DERRIDAI_DEFAULT_MIROSTAT", "0"))
DEFAULT_MIROSTAT_ETA = float(os.getenv("DERRIDAI_DEFAULT_MIROSTAT_ETA", "0.9"))
DEFAULT_MIROSTAT_TAU = float(os.getenv("DERRIDAI_DEFAULT_MIROSTAT_TAU", "5.0"))
DEFAULT_TOP_K = int(os.getenv("DERRIDAI_DEFAULT_TOP_K", "0"))
DEFAULT_TOP_P = float(os.getenv("DERRIDAI_DEFAULT_TOP_P", "1.0"))


class LLMClient:
    """Provider adapter with deterministic-by-default scholarly generation settings."""

    def __init__(
        self,
        model: str = DEFAULT_CHAT_MODEL,
        temperature: float = DEFAULT_CHAT_TEMPERATURE,
        server_url: str = DEFAULT_CHAT_BASE_URL,
        reasoning: bool | str = DEFAULT_REASONING,
        num_ctx: int = DEFAULT_NUM_CTX,
        mirostat: int = DEFAULT_MIROSTAT,
        mirostat_eta: float = DEFAULT_MIROSTAT_ETA,
        mirostat_tau: float = DEFAULT_MIROSTAT_TAU,
        top_k: int = DEFAULT_TOP_K,
        top_p: float = DEFAULT_TOP_P,
    ):
        self.generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)
        self.model = str(model)
        self.temperature = temperature
        self.server_url = server_url
        self.reasoning = reasoning
        self.num_ctx = num_ctx
        self.mirostat = mirostat
        self.mirostat_eta = mirostat_eta
        self.mirostat_tau = mirostat_tau
        self.top_k = top_k
        self.top_p = top_p
        self.chats: dict[str, ChatOllama] = {"defaults": self._build_chat(self.model)}
        LOG.info("Initialized LLM adapter: %s", self.get_config_string())

    def _build_chat(self, model: str) -> ChatOllama:
        return ChatOllama(
            model=model,
            temperature=self.temperature,
            base_url=self.server_url,
            reasoning=self.reasoning,
            num_ctx=self.num_ctx,
            num_predict=-2,
            mirostat=self.mirostat,
            mirostat_eta=self.mirostat_eta,
            mirostat_tau=self.mirostat_tau,
            repeat_last_n=64,
            repeat_penalty=1.1,
            top_k=self.top_k,
            top_p=self.top_p,
            keep_alive=-1,
        )

    def get_config_string(self) -> str:
        return (
            f"model: {self.model} | temperature: {self.temperature} | "
            f"server_url: {self.server_url} | reasoning: "
            f"{'enabled' if self.reasoning else 'disabled'} | mirostat: {self.mirostat} | "
            f"num_ctx: {self.num_ctx} | top_k: {self.top_k} | top_p: {self.top_p}"
        )

    async def prompt(
        self,
        params: dict,
        model: str = "defaults",
        extract_json: bool = False,
    ) -> tuple[str | dict, AIMessage]:
        start = time.perf_counter()
        chat = self.chats.get(model)
        if chat is None:
            raise KeyError(f"Unknown configured chat profile: {model}")

        template = ChatPromptTemplate([("user", params.get("user", "{prompt}"))])
        prompt_value = template.invoke(params.get("template", {}))
        async with self.generation_semaphore:
            response = await chat.ainvoke(prompt_value)

        cleaned = strip_code_fence(str(response.content), extract_json=extract_json)
        if extract_json:
            try:
                cleaned = json.loads(cleaned)
            except Exception as exc:
                LOG.warning("Prompt response is not valid JSON: %s", exc)

        metadata = response.response_metadata or {}
        eval_count = metadata.get("eval_count")
        eval_duration = metadata.get("eval_duration")
        if eval_count and eval_duration:
            LOG.debug(
                "Prompt generated %d tokens at %.1f tokens/s",
                eval_count,
                eval_count / (eval_duration / 1e9),
            )
        LOG.debug("Prompt completed in %.2f seconds", time.perf_counter() - start)
        return cleaned, response
