from logger import Logger

# STANDARD LIBRARIES

# LLM
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma

LOG = Logger.setup("RAG_client")

# Models to test
#   - phi4-mini:3.8b   <-- bigger input context, VERY fast, promising when tuned properly (low entropy)
#   - phi4-mini-reasoning:3.8b
#   - phi4:14b <-- usually best
#   - gemma4:12b <-- very promising, can do 262144 context on 100% GPU even with embeddings model alongside
#   - gemma4:e4b <-- also very promising, perhaps most promising
#   - gemma4:e2b <-- very fast and promising
#   - phi4-reasoning:latest (14b) <-- very slow, not viable
#   - qwen3.5:9b
#   - qwen3.5:4b
#   - deepseek-r1:8b
#   - mistral-nemo:12b <-- interesting, but doesn't fit on GPU
#   - deepseek <-- do not bother
#   - llama3.1:8b <-- good balance of context and performance, fits on GPU
#   - llama3.2:3b <-- not good enough

DEFAULT_CHAT_MODEL = "gemma4:e4b"
DEFAULT_CHAT_TEMPERATURE = 0.4
DEFAULT_CHAT_BASE_URL = "http://localhost:11434"
DEFAULT_CHAT_TIMEOUT = 120.0
DEFAULT_EMBEDDING_MODEL = "bge-m3:latest"
DEFAULT_STORE_PERSIST_DIRECTORY = "./chroma_db_local7"
DEFAULT_REASONING_FLAG = False

embeddings = OllamaEmbeddings(
    model=DEFAULT_EMBEDDING_MODEL,
    base_url=DEFAULT_CHAT_BASE_URL,
)

class RAG_LLM:
    chats = {}
    embeddings = {}
    stores = {}
    key = "defaults"
    def __init__(self):
        self.chats["defaults"] = ChatOllama(
            model=DEFAULT_CHAT_MODEL,
            temperature=DEFAULT_CHAT_TEMPERATURE,
            base_url=DEFAULT_CHAT_BASE_URL,
            timeout=DEFAULT_CHAT_TIMEOUT,
            reasoning=DEFAULT_REASONING_FLAG,
            num_ctx=262144,
            num_predict=-2,     # Default 128, -1 = infinite, -2 = fill context. Prefer -2
            mirostat=2,  # Default 0, 0 = off, 1 = basic, 2 = advanced. Prefer 2 for better control of output randomness.
            mirostat_eta=0.9,  # Default 0.1, higher = more responsive to feedback from generated text. Prefer 0.2
            mirostat_tau=3.0,  # Default 5.0, lower = more stable responses. Prefer 5.0
            repeat_last_n=64,   # Default 64, sets how far back to look to prevent token repetition. Prefer 64
            repeat_penalty=1.1, # Default 1.1, higher penalizes repetition more strongly. Prefer 1.1
            top_k=40,           # Default 40, higher gives more diverse answers. Prefer 40
            top_p=0.9,          # Default 0.9, higher will lead to more diverse text. Prefer 0.9
            keep_alive=-1
        )
        self.stores["defaults"] = Chroma(
            persist_directory=DEFAULT_STORE_PERSIST_DIRECTORY,
            embedding_function=embeddings,
        )

    def switch(self, key: str):
        self.key = key

    def chat(self, key: str = None):
        return self.chats[key if key else self.key]

    def store(self, key: str = ""):
        key = key if key else self.key
        store = self.stores.get(key, None)
        if store:
            return store
        elif key:
            self.stores[key] = Chroma(
                persist_directory=f"{DEFAULT_STORE_PERSIST_DIRECTORY}_{key}",
                embedding_function=embeddings,
            )
            self.key = key
            return self.stores[key]
    def embeddings(self, key: str = None):
        return embeddings