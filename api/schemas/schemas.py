from pydantic import BaseModel, Field
from typing import Any, List, Optional, TypedDict, NotRequired
from enum import StrEnum

class QueryRequest(BaseModel):
    """
    Schema for the POST request body for the /v1/query endpoint.
    Represents a complex data query payload.
    """
    prompt: str = Field(..., description="The main query prompt provided by the user.") 
    # query_type: str = Field(..., description="The specific type of query (e.g., 'user_data', 'article_summary').")
    # input_params: dict = Field(..., description="A dictionary of key-value parameters specific to the query_type.")
    # context_id: Optional[str] = Field(None, description="Optional ID linking the query to existing context data.")
    # limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return.")

class QueryItem(BaseModel):
    """
    Schema for a single, returned data item.
    """
    id: str = Field(..., description="Unique identifier for the returned item.")
    title: str = Field(..., description="The primary title or name of the result.")
    content_snippet: str = Field(..., description="A concise snippet of the main content, suitable for quick display.")
    tags: List[str] = Field(..., description="Relevant metadata tags associated with the item.")
    source: str = Field(..., description="The origin or source of the data (e.g., 'Database', 'API', 'File').")
    is_published: bool = Field(..., description="Flag indicating if the item is publicly available.")

class QueryResponse(BaseModel):
    """
    Schema for the overall successful POST response for the /v1/query endpoint.
    """
    total_results: int = Field(..., description="The total number of records found matching the query criteria.")
    results: List[QueryItem] = Field(..., description="A list of structured data items that match the query.")
    generated_at: str = Field(..., description="Timestamp when the query was processed.")

class GenericResponse(BaseModel):
    """
    Schema for a generic API response.
    """
    content: Any = Field(..., description="The main content of the response, which can include text or structured data.")
    results: Any = Field(..., description="Query results")

class JobStartResponse(BaseModel):
    """
    Schema for the response returned when a job is started.
    """
    job_id: str = Field(..., description="The unique identifier for the job associated with this response.")

class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="The unique identifier for the completed job.")
    status: str = Field(..., description="The current status of the job (e.g., 'pending', 'done').")
    result: Optional[GenericResponse] = Field(None, description="The result of the completed job.")

class DerridAIQueryMetadata(TypedDict):
    canonical_work_ids: list[str]
    works_referenced: list[str]
    canonical_work_ids_works_referenced: list[str]
    materials_languages: list[str]
    institutions_referenced: list[str]
    locations_referenced: list[str] 
    persons_referenced: list[str]
    events_referenced: list[str]
    groups_referenced: list[str]
    languages_referenced: list[str]
    limit: int
    response_language: str
    prompt_languages: list[str]
    document_languages: list[str]
    prompt: NotRequired[str | None]
    prompt_fr: NotRequired[str | None]
    keywords: NotRequired[list[str] | None]
    keywords_fr: NotRequired[list[str] | None]
    prompt_query: NotRequired[str | None]
    prompt_query_fr: NotRequired[str | None]
    prompt_instructions: NotRequired[str | None]

class LLMModels(StrEnum):
    DEEPSEEK_14B = "deepseek-r1:14b" # Rather slow
    GEMMA4_E2B = "gemma4:e2b"
    GEMMA4_E4B = "gemma4:e4b"
    GEMMA4_E4B_MTB = "hf.co/unsloth/gemma-4-E4B-it-GGUF:Q8_0"
    GEMMA4_12B = "gemma4:12b"
    GEMMA4_12B_MTB = "4skl/gemma4-12b-mtp:latest"
    GEMMA4_26B = "hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:UD-IQ4_XS" # Strong candidate for parsing text, but 5%/95% CPU/GPU even with small context
    GPT_OSS_20B = "gpt-oss:20b"
    GRANITE_3B = "granite4.2:3b"    # Very fast, but not smart when it comes to text
    GRANITE_8B = "granite4.2:8b"    # Same as above
    LLAMA_3B = "llama3.2:3b"    # Includes reasoning in output; useless
    ORNITH_9B = "ornith-1.5:9b" # Seemingly the best by far
    ORNITH_35B = "hf.co/AtomicChat/Ornith-1.5-35B-A3B-GGUF:IQ3_XXS" # 15 GB    8%/92% CPU/GPU, ~50t/s
    PHI4_14B = "phi4:14b" # Too slow
    PHI4_MINI_4B = "phi4-mini:3.8b"
    PHI4_MINI_REASONING_4B = "phi4-mini-reasoning:3.8b"
    QWEN_0B = "qwen3.5:0.8b"    # For experimentation only
    QWEN_2B = "qwen3.5:2b"
    QWEN_4B = "qwen3.5:4b"
    QWEN_9B = "qwen3.5:9b"  # Very high precision, low recall for record auditing. Very fast
    QWEN_27B = "hf.co/unsloth/Qwen3.5-27B-GGUF:IQ4_XS"  # Too big-- 13%/87% CPU/GPU 

class Languages(StrEnum):
    ENGLISH = "en"
    FRENCH = "fr"

class RAGSearchTypes(StrEnum):
    MMR = "mmr"
    SIMILARITY = "similarity"