from dataclasses import dataclass
from defaults import (
    OLLAMA_BASE_URL,
    CHAT_MODEL,
    CHAT_TEMPERATURE,
    EMBEDDING_MODEL,
    DB_PATH,
)

@dataclass
class ChatConfig:
    base_url: str = OLLAMA_BASE_URL
    model: str = CHAT_MODEL
    temperature: float = CHAT_TEMPERATURE

@dataclass
class EmbedConfig:
    model: str = EMBEDDING_MODEL
    base_url: str = OLLAMA_BASE_URL

@dataclass
class StoreConfig:
    persist_directory: str = DB_PATH

@dataclass
class LangChainConfig:
    chat: ChatConfig
    embedding: EmbedConfig
    store: StoreConfig

    @classmethod
    def from_defaults(cls) -> "LangChainConfig":
        return cls(
            chat=ChatConfig(),
            embedding=EmbedConfig(),
            store=StoreConfig(),
        )