from pydantic import BaseModel, Field
from typing import Any, Callable, List, Optional, TypedDict, NotRequired

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