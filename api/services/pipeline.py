from pydantic import BaseModel, Field
from typing import Any, Callable, TypeAlias
from schemas.schemas import QueryRequest
import uuid
import time
from logging_config import logging

LOG = logging.getLogger(__name__)

class PipelineStepResult(BaseModel):
    """
    Represents the result of executing a pipeline step.
    """
    result: dict[str, Any] = Field(..., description="The output or result produced by the executed pipeline step.")
    execution_time: float = Field(..., description="Time taken to execute the pipeline step in seconds.")

class PipelineStepContext(BaseModel):
    """
    Represents the context for a pipeline step, including any necessary state or data.
    """
    request: QueryRequest = Field(..., description="The original query request that initiated the pipeline.")
    state: dict = Field(..., description="A dictionary representing the current state or context for the pipeline step.")

PipelineStepCallable: TypeAlias = Callable[
    [
        PipelineStepContext,                # Context
        PipelineStepResult,                 # Predecessor's output
    ],
    Any                                     # Output
]

pipeline_count = 0
class PipelineStep(BaseModel):
    iterations: int = Field(1, description="Number of times to execute this pipeline step.")
    context: PipelineStepContext = Field(..., description="The context in which this pipeline step operates.")
    fn: PipelineStepCallable = Field(..., description="The function to be executed for this pipeline step.")
    name: str = Field(..., description="A human-readable name for the pipeline step.")
    id: str = Field(..., description="A unique identifier for the pipeline step.")
    position: int = Field(..., description="The position of the pipeline step in the overall pipeline sequence.")
    completed: bool = Field(False, description="Indicates whether the pipeline step has been completed.")
    def __init__(
            self,
            fn: PipelineStepCallable,
            context: PipelineStepContext,
            name: str = f"pipeline-{pipeline_count}",
            id: str = str(uuid.uuid4()),
            position: int = -1,
    ):
        super().__init__(id=id, name=name, fn=fn, context=context, position=position)
        global pipeline_count
        pipeline_count += 1
        self.position = int(pipeline_count)
    async def execute(self,
            last_result: PipelineStepResult = PipelineStepResult(result={}, execution_time=0.0)
    ) -> PipelineStepResult:
        """
        Executes the function associated with this pipeline step asynchronously.
        """
        start = time.perf_counter()
        LOG.info("Beginning execution of pipeline step #%d '%s' with ID '%s'...", self.position, self.name, self.id)
        for iteration in range(self.iterations):
            LOG.info("Executing iteration %d of %d for pipeline step #%d '%s' with ID '%s'...", iteration + 1, self.iterations, self.position, self.name, self.id)
            last_result = await self.fn(self.context, last_result)
        self.completed = True
        LOG.info("Finished in %.4f seconds execution of pipeline step #%d '%s' with ID '%s'.", time.perf_counter() - start, self.position, self.name, self.id)
        return last_result


class PipelineService():

    context: PipelineStepContext
    steps: list[PipelineStep] = []

    def __init__(self, context: PipelineStepContext, steps: list[PipelineStep] = []):
        # Initialize any necessary attributes or services here
        self.context = context
        self.steps = steps

    def start_pipeline(self, pipeline_id):
        # Logic to start the pipeline with the given ID
        pass

    def stop_pipeline(self, pipeline_id):
        # Logic to stop the pipeline with the given ID
        pass

    def get_pipeline_status(self, pipeline_id):
        # Logic to retrieve the status of the pipeline with the given ID
        pass

    def list_pipelines(self):
        # Logic to list all available pipelines
        pass