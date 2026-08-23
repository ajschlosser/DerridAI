from langchain_ollama import ChatOllama, OllamaEmbeddings
#from langchain_core.prompts import ChatPromptTemplate
import subprocess
import time
from typing import Callable, Tuple

# --------------------------------------------------------------------------- #
# Helper: run a shell command and return its stdout + stderr
# --------------------------------------------------------------------------- #
def run_command(cmd: str) -> Tuple[str, str]:
    """Run *cmd* and return a tuple (stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=False,          # we pass the command as a list for safety
        capture_output=True,
        text=True,            # return str instead of bytes
    )
    return result.stdout, result.stderr

print("Loading gpt-oss:20b llm")

llm = ChatOllama(
    model='gpt-oss:20b',
    base_url='http://localhost:11434',
    temperature=0.5,
    timeout=45.0,  # e.g., 45 s
)

prompt_template = "Give me an intelligent, interesting academic question to ask about Jacques Derrida's philosophy. It must be less than 270 characters. ONLY USE SINGLE QUOTES, NO DOUBLE QUOTES. No characters that need to be escaped. AVOID OVERINDEXING ON COMMON DERRIDEAN TOPICS LIKE DECONSTRUCTION, DIFFERANCE, ETC."

#prompt = ChatPromptTemplate.from_template(prompt_template).format()

print("invoking wisdom with prompting")

response = llm.invoke(prompt_template)

print(response.content)

print("asking jackie")

# Build the exact command string (you could also build a list)
cmd = (
    'python3',
    'rag7.py',
    '--p',f'{response.content}'
)

# Run the command and capture the output
stdout, stderr = run_command(cmd)

# Store the result in a variable
global response_text
response_text = stdout.strip()

print("JACKIE SAYS:", response_text, stderr.strip())