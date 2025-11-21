import motor.motor_asyncio
from beanie import init_beanie
from typing import Dict, Any
from datetime import datetime
import os

from .db_schemas.reportSchema import ReportModel, StepData, ResearchedSection

async def init_database():
    """Initializes the database connection and Beanie with the ReportModel."""
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI environment variable not set.")
    
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    await init_beanie(database=client.risk_assessment_db, document_models=[ReportModel])
    print("✓ Beanie ODM initialized successfully.")

async def create_report_run(company_name: str) -> str:
    """Creates a new report document and returns its run_id."""
    new_run = ReportModel(company_name=company_name)
    await new_run.insert()
    print(f"✓ Created new report run for {company_name} with run_id: {new_run.run_id}")
    return new_run.run_id

async def update_report_step(run_id: str, step_name: str, result: Dict, context: Dict):
    """Finds a report run and adds or updates a step's data."""
    report_run = await ReportModel.find_one(ReportModel.run_id == run_id)
    if not report_run:
        print(f"✗ Error: Could not find report run with id {run_id}")
        return

    step_data = StepData(result=result, context=context)
    report_run.steps[step_name] = step_data
    report_run.updated_at = datetime.utcnow()
    await report_run.save()
    print(f"✓ Saved step '{step_name}' to DB for run_id: {run_id}")

async def add_researched_section(run_id: str, index: int, name: str, content: str):
    """Adds a completed research section to the report run."""
    report_run = await ReportModel.find_one(ReportModel.run_id == run_id)
    if not report_run:
        print(f"✗ Error: Could not find report run with id {run_id}")
        return

    section_data = ResearchedSection(section_index=index, section_name=name, content=content)
    report_run.researched_sections.append(section_data)
    report_run.updated_at = datetime.utcnow()
    await report_run.save()
    print(f"✓ Saved Section {index + 1}: '{name}' to DB.")

async def finalize_report_run(run_id: str, final_content: str, conclusion_and_refs: Dict):
    """Updates the final report content, adds final step, and marks the run as complete."""
    report_run = await ReportModel.find_one(ReportModel.run_id == run_id)
    if not report_run:
        print(f"✗ Error: Could not find report run with id {run_id}")
        return

    # Save the finalizer step data
    finalizer_step = StepData(result=conclusion_and_refs, context={"message": "Final report assembled."})
    report_run.steps['finalizer'] = finalizer_step
    
    # Save the final report and update status
    report_run.final_report_content = final_content
    report_run.status = "completed"
    report_run.updated_at = datetime.utcnow()
    await report_run.save()
    print(f"✓ Finalized and completed run in DB for run_id: {run_id}")