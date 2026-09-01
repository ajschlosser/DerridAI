import asyncio
import os
import time
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
import logging

from utils.strip_code_fence import strip_code_fence
LOG = logging.getLogger(__name__)

MAX_CONCURRENT_GENERATIONS = 1

DEFAULT_CHAT_MODEL = "gemma4:e4b"
DEFAULT_CHAT_TEMPERATURE = 0.4
DEFAULT_CHAT_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434",
)
DEFAULT_EMBEDDING_MODEL = "bge-m3:latest"
DEFAULT_STORE_PERSIST_DIRECTORY = "./chroma_db_local7"
DEFAULT_REASONING_FLAG = False
DEFAULT_NUM_CTX = 262144
DEFAULT_MIROSTAT = 2
DEFAULT_MIROSTAT_ETA = 0.9
DEFAULT_MIROSTAT_TAU = 3.0

class LLMClient:
    chats: dict[str, ChatOllama] = {}
    server_url: str = DEFAULT_CHAT_BASE_URL
    reasoning: bool = DEFAULT_REASONING_FLAG
    temperature: float = DEFAULT_CHAT_TEMPERATURE
    model: str = DEFAULT_CHAT_MODEL
    num_ctx: int = DEFAULT_NUM_CTX
    mirostat: int = DEFAULT_MIROSTAT
    mirostat_eta: float = DEFAULT_MIROSTAT_ETA
    mirostat_tau: float = DEFAULT_MIROSTAT_TAU
    def __init__(self):
        self.generation_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_GENERATIONS
        )

        LOG.debug(f"Initializing LLMClient... chat model: {self.model} | temperature: {self.temperature} | server url: {self.server_url} | reasoning: {'disabled' if not self.reasoning else 'enabled'}")
        self.chats["defaults"] = ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.server_url,
            reasoning=self.reasoning,
            num_ctx=self.num_ctx,
            num_predict=-2,                     # Default 128, -1 = infinite, -2 = fill context. Prefer -2
            mirostat=self.mirostat,             # Default 0, 0 = off, 1 = basic, 2 = advanced. Prefer 2 for better control of output randomness.
            mirostat_eta=self.mirostat_eta,     # Default 0.1, higher = more responsive to feedback from generated text. Prefer 0.2
            mirostat_tau=self.mirostat_tau,     # Default 5.0, lower = more stable responses. Prefer 5.0
            repeat_last_n=64,                   # Default 64, sets how far back to look to prevent token repetition. Prefer 64
            repeat_penalty=1.1,                 # Default 1.1, higher penalizes repetition more strongly. Prefer 1.1
            top_k=40,                           # Default 40, higher gives more diverse answers. Prefer 40
            top_p=0.9,                          # Default 0.9, higher will lead to more diverse text. Prefer 0.9
            keep_alive=-1
        )

    def get_config_string(self) -> str:
        return f"model: {self.model} | temperature: {self.temperature} | server_url: {self.server_url} | reasoning: {'disabled' if not self.reasoning else 'enabled'} | mirostat: {self.mirostat} | mirostat_eta: {self.mirostat_eta} | mirostat_tau: {self.mirostat_tau} | num_ctx: {self.num_ctx}"

    async def prompt(self, params: dict, model: str = "defaults", extract_json=False) -> tuple:
        start = time.perf_counter()
        default_system_prompts = [
            "Your name is DerridAI.",
            "You are a helpful AI research assistant specializing in the works of Jacques Derrida.",
        ]
        system_messages = params["system"] if "system" in params else [("system", message) for message in default_system_prompts]
        user_messages = [("user", params["user"])] if "user" in params else [("user", "{prompt}")]
        template = ChatPromptTemplate([
            *system_messages,
            *user_messages,
        ])
        prompt_value = template.invoke(params["template"])
        async with self.generation_semaphore:
            response = await self.chats[model].ainvoke(prompt_value)
        LOG.info("aiinvoke response: %s", response.content)
        cleaned_response = strip_code_fence(str(response.content), extract_json=extract_json)
        if extract_json:
            try:
                cleaned_response = json.loads(cleaned_response)
            except Exception as e:
                LOG.warning("Prompt response is not in JSON format: %s", e)
        LOG.debug("Prompt generation and response completed in %.2f seconds", time.perf_counter() - start)
        return cleaned_response, response