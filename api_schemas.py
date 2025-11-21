from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ReportSummary(BaseModel):
    """A simplified summary of a report for the 'get all reports' API endpoint."""
    runId: str
    company_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    # This will allow the model to be created from a Beanie document object
    class Config:
        from_attributes = True

class GetAllReportsResponse(BaseModel):
    """The response model for the get-all-reports endpoint."""
    reports: List[ReportSummary]