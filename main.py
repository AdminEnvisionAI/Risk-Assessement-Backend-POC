# from deep_research.graph import agent_graph
# from deep_research import db_manager
# from deep_research.state import AgentState # Good practice to import the state type
# import uuid
# import os
# import asyncio
# import json
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # IMPORTANT: Make sure you have a .env file in your root directory with:
# # MONGO_URI="your_mongodb_connection_string"

# async def main():
#     """
#     Asynchronous main function to run the risk assessment and research process.
#     """
#     # ========== COMPANY INPUT ==========
#     # Change this to analyze different companies
#     COMPANY_NAME = "TCS"
    
#     print("\n" + "="*100)
#     print(f"ADVANCED RISK ASSESSMENT & RESEARCH SYSTEM")
#     print("="*100)
#     print(f"\nCompany: {COMPANY_NAME}")
#     print("\nThis system will:")
#     print("  1. Analyze the company and identify risk parameters (Schema Designer)")
#     print("  2. Assess each risk parameter with evidence (Risk Assessor)")
#     print("  3. Validate and format the risk assessment (Report Validator)")
#     print("  4. Create research sections from the risk assessment")
#     print("  5. Conduct deep research on each risk category")
#     print("  6. Generate a comprehensive risk assessment report\n")
#     print("="*100 + "\n")
    
#     # --- DATABASE INITIALIZATION ---
#     print("Initializing database connection...")
#     await db_manager.init_database()
    
#     print(f"Creating new report run for '{COMPANY_NAME}' in the database...")
#     run_id = await db_manager.create_report_run(company_name=COMPANY_NAME)
    
#     if not run_id:
#         print("✗ Failed to create a database run. Aborting.")
#         return
    
#     print(f"✓ Database run created with ID: {run_id}")
#     # --- END DATABASE INITIALIZATION ---
    
#     # Configuration for the LangGraph stream
#     thread_config = {
#         "configurable": {
#             "thread_id": str(uuid.uuid4()),
#             "max_queries": 3,
#             "search_depth": 3,
#             "num_reflections": 2,
#             "temperature": 0.7,
#             "run_id": run_id,
#             "section_delay_seconds": 3
#         },
#         "recursion_limit": 100
#     }

#     # Create local output directories if they don't exist
#     os.makedirs("logs/section_content", exist_ok=True)
#     os.makedirs("reports", exist_ok=True)

#     # Define the initial state for the graph, including the run_id
#     initial_state: AgentState = {
#         "run_id": run_id,
#         "company_name": COMPANY_NAME,
#         "topic": f"{COMPANY_NAME} Risk Assessment Report",
#         "outline": f"Comprehensive risk assessment for {COMPANY_NAME}",
#         "messages": []
#         # Other state fields will be populated as the graph runs
#     }

#     # Run the integrated graph
#     log_file_path = "logs/agent_logs.jsonl"
#     print(f"\nStarting agent graph execution... Full logs at: {log_file_path}\n")

#     with open(log_file_path, "w", encoding="utf-8") as f:
#         #
#         # === KEY CHANGE IS HERE ===
#         # Use 'async for' and 'agent_graph.astream()' to work with your async nodes.
#         # This correctly uses the running event loop instead of trying to start a new one.
#         #
#         async for event in agent_graph.astream(initial_state, config=thread_config):
#             # Log all events as JSON lines for better parsing
#             f.write(json.dumps(event, default=str) + "\n")

#             # Print relevant events to console
#             # The event dictionary key indicates which node just finished
#             event_key = list(event.keys())[0]
#             print("event_key----------------->",event_key)

#             if event_key == "risk_schema_designer":
#                 print("✓ Risk Schema Designer completed")
#             elif event_key == "risk_assessor":
#                 print("✓ Risk Assessor completed")
#             elif event_key == "risk_validator":
#                 print("✓ Risk Validator completed")
#             elif event_key == "report_structure_planner":
#                 print("✓ Report Structure Planner completed")
#             elif event_key == "finalizer":
#                 print("\n" + "="*100)
#                 print("FINAL REPORT COMPLETE")
#                 print("="*100)
#                 print(f"\n✓ Full report run saved to MongoDB under run_id: {run_id}")
#                 print(f"✓ Final report saved locally to: reports/{COMPANY_NAME} Risk Assessment Report.md")
#                 print(f"✓ Detailed section content saved locally in: logs/section_content/")
#                 print("\n" + "="*100 + "\n")
#             # Other nodes like 'queue_next_section' and 'research_agent' run silently
            
# if __name__ == "__main__":
#     # Run the main asynchronous function
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\nProcess interrupted by user. Exiting.")




import uuid
import os
import asyncio
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from deep_research.graph import agent_graph
from deep_research import db_manager
from deep_research.state import AgentState
from api_schemas import ReportSummary, GetAllReportsResponse # (Assuming api_schemas.py exists)
from deep_research.db_schemas.reportSchema import ReportModel
from fastapi.middleware.cors import CORSMiddleware
# --- 1. SETUP ---
# Load environment variables
load_dotenv()

# Create the FastAPI app instance
app = FastAPI(
    title="Deep Research API & Worker",
    description="API to trigger and retrieve risk assessment reports.",
    version="1.0.0"
)

origins = [
    "*"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. REPORT GENERATION LOGIC ---
# We move your original main logic into a function that can be called in the background.

async def run_report_generation(company_name: str):
    """
    The core logic for generating a single report. This will run in the background.
    """
    print("\n" + "="*100)
    print(f"BACKGROUND TASK STARTED: Generating report for {company_name}")
    print("="*100)
    
    # --- Database Record Creation ---
    run_id = await db_manager.create_report_run(company_name=company_name)
    if not run_id:
        print(f"✗ CRITICAL ERROR: Failed to create a database run for {company_name}. Aborting background task.")
        return

    print(f"✓ Database run created with ID: {run_id}")
    
    # --- LangGraph Configuration ---
    thread_config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "run_id": run_id,
            "max_queries": 5, # You can adjust these
            "search_depth": 3,
            "num_reflections": 2,
            "temperature": 0.1,
            "section_delay_seconds": 2
        },
        "recursion_limit": 100
    }
    
    # --- Initial State for the Graph ---
    initial_state: AgentState = {
        "company_name": company_name,
        "topic": f"{company_name} Risk Assessment Report",
        "outline": f"Comprehensive risk assessment for {company_name}",
        "messages": [],
        "tavily_api_keys": [os.getenv("TAVILY_API_KEY")], # You can add more keys here
        "search_count": 0
    }

    # --- Run the Graph ---
    try:
        async for event in agent_graph.astream(initial_state, config=thread_config):
            event_key = list(event.keys())[0]
            print(f"--- Graph Event: {event_key} ---")
        
        print("\n" + "="*100)
        print(f"BACKGROUND TASK COMPLETE: Report for {company_name} finished.")
        print("="*100)
    
    except Exception as e:
        print(f"✗ CRITICAL ERROR during graph execution for {company_name} (run_id: {run_id}): {e}")
        # You can also update the DB status to 'failed' here
        report_run = await ReportModel.find_one(ReportModel.runId == run_id)
        if report_run:
            report_run.status = "failed"
            await report_run.save()

# --- 3. API ENDPOINTS ---

# Pydantic model for the request body of the generate endpoint
class GenerateReportRequest(BaseModel):
    company_name: str

@app.on_event("startup")
async def startup_event():
    """Initializes the database connection when the API server starts."""
    print("Server starting up...")
    await db_manager.init_database()
    print("Database connection established.")

@app.post("/generate-report", status_code=202, tags=["Reports"])
async def generate_report(request: GenerateReportRequest, background_tasks: BackgroundTasks):
    """
    Triggers the report generation process in the background.
    Responds immediately to the client.
    """
    company_name = request.company_name
    if not company_name or len(company_name) < 2:
        raise HTTPException(status_code=400, detail="A valid company_name is required.")
    
    print(f"Received request to generate report for: {company_name}")
    
    # Add the long-running task to the background
    background_tasks.add_task(run_report_generation, company_name)
    
    # Immediately return a response to the frontend
    return {"message": f"Report generation for '{company_name}' has been started in the background."}


@app.post(
    "/get-all-reports"
)
async def get_all_reports():
    """Retrieves a list of summaries for all reports in the database."""
    try:
        all_report_docs = await ReportModel.find(ReportModel.status == "completed",
            sort=[("created_at", -1)],
            limit=100
        ).to_list()
        return {"reports": all_report_docs}
    except Exception as e:
        print(f"Error fetching all reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reports from the database.")

# --- 4. RUN THE SERVER ---
# This part is for running the server directly from the command line.

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    # This will run the FastAPI server when you execute 'python main.py'
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)