from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List, Annotated
from datetime import datetime
import uuid

# ===================================================================
# Sub-models to structure the data within the main report document
# ===================================================================

class StepData(BaseModel):
    """Represents the data captured for a single step in the process."""
    status: str = "completed"
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    result: Dict[str, Any]  # The main output of the node
    context: Dict[str, Any]  # The key inputs that led to the result

class ResearchedSection(BaseModel):
    """Represents a single, fully researched and written section of the report."""
    section_index: int
    section_name: str
    content: str  # The final markdown content for this section
    completed_at: datetime = Field(default_factory=datetime.utcnow)

# ===================================================================
# The main Beanie Document for a Report Run
# ===================================================================

class ReportModel(Document):
    """
    A comprehensive document that tracks the entire process of generating a 
    risk assessment report for a single company. Each document is one "run".
    """
    run_id:  Annotated[str, Indexed(unique=True)] = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    status: str = "in_progress"  # Can be 'in_progress', 'completed', 'failed'
    
    # This dictionary will store the output of each major, one-off step.
    # The key will be the step name (e.g., 'risk_schema_design').
    steps: Dict[str, StepData] = {}
    
    # This list will store the output of the looped research process.
    researched_sections: List[ResearchedSection] = []
    
    # The final, complete report content is stored here at the end.
    final_report_content: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reports" # This will be the collection name in MongoDB

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }