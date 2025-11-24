from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import (
    ChatPromptTemplate, 
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate, 
    MessagesPlaceholder
)
from langchain_core.messages import HumanMessage
from langgraph.types import Command, Send
from typing import Literal, Dict
from tavily import TavilyClient
from .state import AgentState, ResearchState
from .configuration import Configuration
from .utils import init_llm, rate_limit_delay
from .prompts import (
    SECTION_KNOWLEDGE_SYSTEM_PROMPT_TEMPLATE,
    QUERY_GENERATOR_SYSTEM_PROMPT_TEMPLATE,
    RESULT_ACCUMULATOR_SYSTEM_PROMPT_TEMPLATE,
    REFLECTION_FEEDBACK_SYSTEM_PROMPT_TEMPLATE,
    FINAL_SECTION_FORMATTER_SYSTEM_PROMPT_TEMPLATE,
    FINALIZER_SYSTEM_PROMPT_TEMPLATE
)
from .risk_prompts import (
    SCHEMA_SYSTEM_PROMPT,
    ASSESS_SYSTEM_PROMPT,
    VALIDATOR_SYSTEM_PROMPT
)
from .struct import (
    Section,
    Sections,
    Queries,
    SearchResult,
    SearchResults,
    Feedback,
    ConclusionAndReferences
)
import time
import os
import json
import re
from . import db_manager
import asyncio
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io


# async def content_extractor_node(state: ResearchState, config: RunnableConfig):
#     """
#     Downloads content from URLs, handling both HTML and PDF files,
#     and replaces the original raw_content from Tavily search.
#     """
#     print("\n--- Node: Content Extractor ---")
    
#     updated_search_results = []
#     search_results = state["search_results"]

#     for search_result_group in search_results:
#         # Create a new list to hold results with updated content
#         processed_results_for_group = []
        
#         for result in search_result_group.results:
#             print(f"-> Extracting content from: {result.url}")
#             try:
#                 headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
#                 response = requests.get(result.url, headers=headers, timeout=10)
#                 response.raise_for_status() # Raise an exception for bad status codes

#                 # Clone the original result to modify its content
#                 updated_result = result.copy()

#                 if result.url.lower().endswith('.pdf'):
#                     # Handle PDF files
#                     with io.BytesIO(response.content) as f:
#                         reader = PdfReader(f)
#                         pdf_text = ""
#                         for page in reader.pages:
#                             pdf_text += page.extract_text() or ""
                        
#                         # Limit the content size to prevent overwhelming the LLM
#                         updated_result.raw_content = pdf_text[:8000] # Increased limit for valuable PDFs
#                         print("   ✓ Successfully extracted text from PDF.",updated_result.raw_content)

#                 else:
#                     # Handle HTML files
#                     soup = BeautifulSoup(response.content, 'html.parser')
#                     # A simple text extraction, can be improved (e.g., using newspaper3k)
#                     for script in soup(["script", "style"]):
#                         script.extract()
                    
#                     text = soup.get_text(separator='\n', strip=True)
#                     updated_result.raw_content = text[:4000] # Standard limit for HTML
#                     print("   ✓ Successfully scraped text from HTML.",updated_result.raw_content)

#                 processed_results_for_group.append(updated_result)

#             except requests.exceptions.RequestException as e:
#                 print(f"   ✗ Failed to download {result.url}: {e}")
#                 # Optionally, you can keep the original result with Tavily's snippet
#                 # processed_results_for_group.append(result)
#                 continue # Or just skip failed ones
#             except Exception as e:
#                 print(f"   ✗ An error occurred processing {result.url}: {e}")
#                 continue

#         # Add the processed group to the final list
#         if processed_results_for_group:
#             updated_search_results.append(
#                 SearchResults(query=search_result_group.query, results=processed_results_for_group)
#             )

#     return {"search_results": updated_search_results}



async def content_extractor_node(state: ResearchState, config: RunnableConfig):
    """
    Downloads content from URLs, handling both HTML and PDF files,
    replaces the original raw_content from Tavily search, and saves a record
    of the extracted content to the database for the current section.
    """
    print("\n--- Node: Content Extractor ---")
    
    # --- Step 1: Get necessary info from state and config ---
    updated_search_results = []
    search_results = state.get("search_results", [])
    run_id = config["configurable"]["run_id"]
    current_section_index = state.get("current_section_index", "unknown_section")
    
    # This list will hold records for DB logging
    extracted_content_for_db = []

    # --- Step 2: Loop through search results and extract content ---
    for search_result_group in search_results:
        processed_results_for_group = []
        
        for result in search_result_group.results:
            print(f"-> Extracting content from: {result.url}")
            full_content = ""
            status = "failed"
            
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.get(result.url, headers=headers, timeout=15)
                response.raise_for_status()

                updated_result = result.copy()

                if result.url.lower().endswith('.pdf'):
                    with io.BytesIO(response.content) as f:
                        reader = PdfReader(f)
                        pdf_text = "".join(page.extract_text() or "" for page in reader.pages)
                        full_content = pdf_text
                        updated_result.raw_content = full_content[:8000] # Content for the LLM
                        status = "success_pdf"
                        print("   ✓ Successfully extracted text from PDF.")
                else:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.decompose()
                    text = soup.get_text(separator='\n', strip=True)
                    full_content = text
                    updated_result.raw_content = full_content[:4000] # Content for the LLM
                    status = "success_html"
                    print("   ✓ Successfully scraped text from HTML.")

                processed_results_for_group.append(updated_result)

            except Exception as e:
                print(f"   ✗ An error occurred processing {result.url}: {e}")
                status = f"failed_processing: {e}"
            
            # --- Step 3: Prepare a record of this extraction for the DB ---
            extracted_content_for_db.append({
                "url": result.url,
                "title": result.title,
                "status": status,
                "query": getattr(search_result_group, 'query', 'N/A'),
                # We save the full content to the DB, not the truncated version
                "extracted_content": full_content 
            })

        if processed_results_for_group:
            updated_search_results.append(
                SearchResults(query=search_result_group.query, results=processed_results_for_group)
            )
            
    # --- Step 4: Save all extracted content records to the database ---
    if extracted_content_for_db:
        step_name = f"section_{current_section_index}_content_extraction"
        context = {
            "section_name": getattr(state.get("section", {}), 'section_name', 'Unknown Section'),
            "section_index": current_section_index
        }
        # The result_data is the list of records we prepared
        result_data = {"sources_extracted": extracted_content_for_db}
        
        await db_manager.update_report_step(run_id, step_name, result_data, context)
        print(f"✓ Saved records for {len(extracted_content_for_db)} extracted sources to DB for section {current_section_index}.")
    
    # --- Step 5: Return the updated search results for the next node in the graph ---
    return {"search_results": updated_search_results}



# ========= RISK ASSESSMENT NODES =========

async def risk_schema_designer_node(state: AgentState, config: RunnableConfig) -> Dict:
    """
    Designs a dynamic risk schema for the company based on deep analysis.
    This is the first step in the risk assessment process.
    Uses the detailed SCHEMA_SYSTEM_PROMPT from main.py.
    """
    print("\n" + "="*80)
    print("RISK ASSESSMENT PHASE 1: Schema Designer")
    print("="*80)
    
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=0.0  # Use 0 for risk assessment for consistency
    )
    
    # Get Tavily for web search
    tavily_client = TavilyClient(os.getenv("TAVILY_API_KEY", "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"))
    
    company_name = state.get("company_name", "")
    
    print(f"\nAnalyzing company: {company_name}")
    print("Gathering company information...\n")
    
    
    # Reduced searches for speed
    search_queries = [
        f"{company_name} annual report risk factors",
        f"{company_name} recent news"
    ]
    
    search_context = ""
    for query in search_queries:
        print(f"Searching: {query}")
        try:
            response = tavily_client.search(query=query, max_results=2, include_raw_content=False)
            for result in response.get("results", []):
                content = result.get('content', '')[:500]  # Limit content
                # search_context += f"\n\nSource: {result.get('title', 'Unknown')}\n{content}\n"
                search_context += f"\n\nSource: {result.get('title', 'Unknown')}\nURL: {result.get('url', 'N/A')}\nContent: {content}\n"
            await asyncio.sleep(0.2)
        except Exception as e:
            print(f"Search error: {e}")
    
    # Create the prompt
    schema_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SCHEMA_SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(
            template="""
            Design a dynamic risk_schema for company: {company_name}.
            
            Here is the gathered information about the company:
            {search_context}
            
            After analyzing this information, output ONLY the JSON in this format:
            {{"risk_schema": ...}}
            """
        )
    ])
    
    schema_llm = schema_prompt | llm
    
    print("\nGenerating risk schema...")
    rate_limit_delay()
    result =await schema_llm.ainvoke({"company_name": company_name, "search_context": search_context})
    
    # Parse the JSON from the result
    content = result.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    try:
        risk_schema_data = json.loads(content)
        print("\n✓ Risk schema generated successfully")
        run_id = config["configurable"]["run_id"]
        context = {"company_name": company_name, "search_context_summary": search_context[:500] + "..."}
        await db_manager.update_report_step(run_id, "risk_schema_design", risk_schema_data, context)
        
        # Save to file for reference
        os.makedirs("logs", exist_ok=True)
        with open("logs/risk_schema.json", "w", encoding="utf-8") as f:
            json.dump(risk_schema_data, f, indent=2, ensure_ascii=False)
            
        return {"risk_schema": risk_schema_data, "messages": [result]}
    except json.JSONDecodeError as e:
        print(f"\n✗ Error parsing risk schema JSON: {e}")
        print(f"Content: {content}")
        return {"risk_schema": {"error": "Failed to parse schema", "content": content}, "messages": [result]}


async def risk_assessor_node(state: AgentState, config: RunnableConfig) -> Dict:
    """
    Assesses each risk parameter identified in the schema.
    Uses the detailed ASSESS_SYSTEM_PROMPT from main.py.
    """
    print("\n" + "="*80)
    print("RISK ASSESSMENT PHASE 2: Risk Assessor")
    print("="*80)
    
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=0.0
    )
    
    # Get Tavily for web search
    tavily_client = TavilyClient(os.getenv("TAVILY_API_KEY", "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"))
    
    company_name = state.get("company_name", "")
    risk_schema = state.get("risk_schema", {})
    
    print(f"\nAssessing risks for: {company_name}")
    print("Gathering evidence for each risk parameter...\n")
    
    # Reduced searches
    search_queries = [
        f"{company_name} financial statements",
        f"{company_name} operational risks"
    ]
    
    search_context = ""
    for query in search_queries:
        print(f"Searching: {query}")
        try:
            response = tavily_client.search(query=query, max_results=2, include_raw_content=False)
            for result in response.get("results", []):
                content = result.get('content', '')[:500]
                # search_context += f"\n\nSource: {result.get('title', 'Unknown')}\n{content}\n"
                search_context += f"\n\nSource: {result.get('title', 'Unknown')}\nURL: {result.get('url', 'N/A')}\nContent: {content}\n"
            await asyncio.sleep(0.2)
        except Exception as e:
            print(f"Search error: {e}")
    
    # Create the prompt
    assess_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(ASSESS_SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(
            template="""
            You already designed this risk_schema for {company_name}:
            
            {risk_schema}
            
            Here is the gathered information:
            {search_context}
            
            After completing your analysis, output ONLY the JSON:
            {{"assessment": ...}}
            """
        )
    ])
    
    assess_llm = assess_prompt | llm
    
    print("\nGenerating risk assessments...")
    rate_limit_delay()
    result =await assess_llm.ainvoke({
        "company_name": company_name,
        "risk_schema": json.dumps(risk_schema, indent=2),
        "search_context": search_context
    })
    
    # Parse the JSON from the result
    content = result.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    try:
        assessment_data = json.loads(content)
        print("\n✓ Risk assessment completed successfully")
            # --- DB SAVE ---
        run_id = config["configurable"]["run_id"]
        # Context is the schema it was given to work with
        context = {"risk_schema": state.get("risk_schema", {})}
        await db_manager.update_report_step(run_id, "risk_assessment", assessment_data, context)
        # --- END DB SAVE ---
        
        # Save to file for reference
        with open("logs/risk_assessment.json", "w", encoding="utf-8") as f:
            json.dump(assessment_data, f, indent=2, ensure_ascii=False)
            
        return {"risk_assessment": assessment_data, "messages": [result]}
    except json.JSONDecodeError as e:
        print(f"\n✗ Error parsing assessment JSON: {e}")
        print(f"Content: {content}")
        return {"risk_assessment": {"error": "Failed to parse assessment", "content": content}, "messages": [result]}


async def risk_validator_node(state: AgentState, config: RunnableConfig) -> Dict:
    """
    Validates and formats the final risk report.
    Uses the detailed VALIDATOR_SYSTEM_PROMPT from main.py.
    """
    print("\n" + "="*80)
    print("RISK ASSESSMENT PHASE 3: Report Validator")
    print("="*80)
    
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=0.0
    )
    
    company_name = state.get("company_name", "")
    risk_schema = state.get("risk_schema", {})
    risk_assessment = state.get("risk_assessment", {})
    
    print(f"\nValidating risk report for: {company_name}")
    
    # Create the prompt
    validator_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(VALIDATOR_SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(
            template="""
            Company: {company_name}
            
            risk_schema:
            {risk_schema}
            
            assessment:
            {risk_assessment}
            
            Return ONLY the final validated JSON report.
            """
        )
    ])
    
    validator_llm = validator_prompt | llm
    
    print("\nValidating and formatting final report...")
    rate_limit_delay()
    result =await validator_llm.ainvoke({
        "company_name": company_name,
        "risk_schema": json.dumps(risk_schema, indent=2),
        "risk_assessment": json.dumps(risk_assessment, indent=2)
    })
    
    # Parse the JSON from the result
    content = result.content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    try:
        validated_report = json.loads(content)
        print("\n✓ Risk report validated successfully")
            # --- DB SAVE ---
        run_id = config["configurable"]["run_id"]
        context = {
            "risk_schema": state.get("risk_schema", {}),
            "raw_assessment": state.get("risk_assessment", {})
        }
        await db_manager.update_report_step(run_id, "validated_risk_report", validated_report, context)
        # --- END DB SAVE ---
        print("="*80)
        print("RISK ASSESSMENT COMPLETE")
        print("="*80 + "\n")
        
        # Save to file for reference
        with open("logs/validated_risk_report.json", "w", encoding="utf-8") as f:
            json.dump(validated_report, f, indent=2, ensure_ascii=False)
            
        return {"validated_risk_report": validated_report, "messages": [result]}
    except json.JSONDecodeError as e:
        print(f"\n✗ Error parsing validated report JSON: {e}")
        print(f"Content: {content}")
        return {"validated_risk_report": {"error": "Failed to parse report", "content": content}, "messages": [result]}


# ========= REPORT STRUCTURE PLANNER (UPDATED) =========

async def report_structure_planner_node(state: AgentState, config: RunnableConfig) -> Dict:
    """
    Creates a report structure directly from the validated risk assessment data.
    No user interaction - directly converts risk assessment into research sections.
    """
    print("\n" + "="*80)
    print("REPORT STRUCTURE PLANNING: Creating Deep Research Sections")
    print("="*80)
    
    validated_report = state.get("validated_risk_report", {})
    company_name = state.get("company_name", "")
    
    # Create sections directly from the risk assessment
    sections = []
    
    # 1. Executive Summary Section
    sections.append(Section(
        section_name="Executive Summary",
        sub_sections=[
            f"Overview of {company_name}'s risk profile based on comprehensive assessment",
            "Key findings across external and internal risk categories",
            "Critical risk areas requiring immediate attention",
            "Strategic recommendations for risk mitigation"
        ]
    ))
    
    # 2. Introduction Section
    sections.append(Section(
        section_name="Introduction",
        sub_sections=[
            f"Company profile: {company_name}'s business model, operations, and market position",
            "Risk assessment methodology and frameworks used",
            "Scope of risk analysis covering operational, financial, strategic, and regulatory domains",
            "Report structure and how to interpret risk ratings (LOW, MEDIUM, HIGH)"
        ]
    ))
    
    # 3. External Risks - Create sections for each category
    risk_schema = validated_report.get("risk_schema", {}).get("schema", {})
    external_risks = risk_schema.get("external", {})
    
    for category, params in external_risks.items():
        param_descriptions = []
        for param in params:
            param_id = param.get("id", "")
            param_label = param.get("label", "")
            # Get the assessment for this parameter
            assessment_key = f"external.{category.replace(' ', '_').replace('&', 'and').lower()}.{param_id}"
            assessment = validated_report.get("results", {}).get(assessment_key, {})
            rating = assessment.get("rating", "UNKNOWN")
            
            param_descriptions.append(
                f"{param_label} (Current Rating: {rating}): Detailed analysis of this risk factor, "
                f"including current trends, potential impacts, and mitigation strategies specific to {company_name}"
            )
        
        sections.append(Section(
            section_name=f"External Risk Analysis: {category}",
            sub_sections=param_descriptions
        ))
    
    # 4. Internal Risks - Create sections for each category
    internal_risks = risk_schema.get("internal", {})
    
    for category, params in internal_risks.items():
        param_descriptions = []
        for param in params:
            param_id = param.get("id", "")
            param_label = param.get("label", "")
            # Get the assessment for this parameter
            assessment_key = f"internal.{category.replace(' ', '_').replace('&', 'and').lower()}.{param_id}"
            assessment = validated_report.get("results", {}).get(assessment_key, {})
            rating = assessment.get("rating", "UNKNOWN")
            
            param_descriptions.append(
                f"{param_label} (Current Rating: {rating}): In-depth examination of this internal risk, "
                f"including root causes, current controls, and recommended improvements for {company_name}"
            )
        
        sections.append(Section(
            section_name=f"Internal Risk Analysis: {category}",
            sub_sections=param_descriptions
        ))
    
    # 5. Risk Mitigation Strategies
    sections.append(Section(
        section_name="Comprehensive Risk Mitigation Framework",
        sub_sections=[
            "Overview of current risk management practices at {company_name}",
            "Recommended mitigation strategies for HIGH-rated risks",
            "Monitoring and control mechanisms for MEDIUM-rated risks",
            "Best practices and industry benchmarks for risk management",
            "Technology and tools for risk monitoring and reporting"
        ]
    ))
    
    # 6. Industry Benchmarking
    sections.append(Section(
        section_name="Industry Benchmarking and Best Practices",
        sub_sections=[
            f"Comparison of {company_name}'s risk profile with industry peers",
            "Global standards and frameworks (ISO 31000, COSO, etc.)",
            "Leading practices in enterprise risk management",
            "Lessons learned from peer companies in managing similar risks"
        ]
    ))
    
    # 7. Recommendations and Action Plan
    sections.append(Section(
        section_name="Strategic Recommendations and Action Plan",
        sub_sections=[
            "Prioritized risk mitigation roadmap based on assessment findings",
            "Short-term actions (0-6 months) for critical risks",
            "Medium-term initiatives (6-18 months) for strategic improvements",
            "Long-term vision for building resilient risk management capabilities",
            "Key performance indicators (KPIs) for tracking risk mitigation progress"
        ]
    ))
    
    print(f"\n✓ Created {len(sections)} research sections from risk assessment")
    print("="*80 + "\n")
    
    # Create a summary message for logging
    report_structure = f"Risk Assessment Report Structure for {company_name}\n\n"
    for i, section in enumerate(sections, 1):
        report_structure += f"{i}. {section.section_name}\n"
        for sub in section.sub_sections:
            report_structure += f"   - {sub}\n"
    
    # ... right before the return statement
    # Create a serializable version for the DB
    sections_for_db = [section.dict() for section in sections]
    result_data = {
        "section_count": len(sections),
        "sections": sections_for_db,
        "report_structure_text": report_structure
    }
    context = {"source_validated_report": validated_report}
    
    # --- DB SAVE ---
    run_id = config["configurable"]["run_id"]
    await db_manager.update_report_step(run_id, "report_structure_plan", result_data, context)
    # --- END DB SAVE ---
    return {
        "sections": sections,
        "current_section_index": 0,
        "report_structure": report_structure,
        "messages": [HumanMessage(content="Report structure created from risk assessment")]
    }


def human_feedback_node(
        state: AgentState, 
        config: RunnableConfig
) -> Command[Literal["queue_next_section"]]:
    """
    Automatically proceeds to section research - no human interaction needed.
    """
    print("\nProceeding with automated research...")
    return Command(
        goto="queue_next_section",
        update={"messages": [HumanMessage(content="Automated research starting")]}
    )


def section_formatter_node(state: AgentState, config: RunnableConfig) -> Command[Literal["queue_next_section"]]:
    """
    This node is now bypassed as sections are created directly in report_structure_planner_node.
    """
    return Command(
        update={},
        goto="queue_next_section"
    )


def queue_next_section_node(state: AgentState, config: RunnableConfig) -> Command[Literal["research_agent", "finalizer"]]:
    """
    Manages the sequential processing of report sections with rate limiting.
    """
    configurable = Configuration.from_runnable_config(config)
    
    if state["current_section_index"] < len(state["sections"]):
        current_section = state["sections"][state["current_section_index"]]
        
        if state["current_section_index"] > 0:
            time.sleep(configurable.section_delay_seconds)
            
        print(f"Processing section {state['current_section_index'] + 1}/{len(state['sections'])}: {current_section.section_name}")
        
        return Command(
            update={"current_section_index": state["current_section_index"] + 1},
            goto=Send("research_agent", {"section": current_section, "current_section_index": state["current_section_index"]})
        )
    else:
        print(f"All {len(state['sections'])} sections have been processed. Generating final report...")
        return Command(goto="finalizer")


def section_knowledge_node(state: ResearchState, config: RunnableConfig):
    """
    Generates initial knowledge and understanding about a section before conducting research.
    """
    return {"knowledge": "Section knowledge generated"}


def query_generator_node(state: ResearchState, config: RunnableConfig):
    """
    Generates search queries based on the current section content and research state.
    """
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=configurable.temperature
    )

    query_generator_system_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            QUERY_GENERATOR_SYSTEM_PROMPT_TEMPLATE.format(max_queries=configurable.max_queries)
        ),
        HumanMessagePromptTemplate.from_template(
            template="Section: {section}\nPrevious Queries: {searched_queries}\nReflection Feedback: {reflection_feedback}"
        ),
    ])
    query_generator_llm = query_generator_system_prompt | llm.with_structured_output(Queries)

    state["reflection_feedback"] = state.get("reflection_feedback", Feedback(feedback=""))
    state["searched_queries"] = state.get("searched_queries", [])

    rate_limit_delay()
    result = query_generator_llm.invoke(state)

    return {"generated_queries": result.queries, "searched_queries": result.queries}


def tavily_search_node(state: ResearchState, config: RunnableConfig):
    """
    Performs web searches using the Tavily search API for each generated query.
    """
    configurable = Configuration.from_runnable_config(config)

    tavily_client = TavilyClient("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")
    queries = state["generated_queries"]
    search_results = []

    for query in queries:
        search_content = []
        response = tavily_client.search(query=query.query, max_results=configurable.search_depth, include_raw_content=True)
        for result in response["results"]:
            if result['raw_content'] and result['url'] and result['title']:
                search_content.append(SearchResult(url=result['url'], title=result['title'], raw_content=result['raw_content']))
        search_results.append(SearchResults(query=query, results=search_content))

    return {"search_results": search_results}


def result_accumulator_node(state: ResearchState, config: RunnableConfig):
    """
    Accumulates and synthesizes search results into coherent content.
    """
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=configurable.temperature
    )

    # Aggressive truncation for speed
    max_chars_per_result = 300
    max_results = 3
    truncated_results = []
    
    result_count = 0
    for search_result_group in state["search_results"]:
        if result_count >= max_results:
            break
            
        truncated_group_results = []
        for result in search_result_group.results:
            if result_count >= max_results:
                break
            truncated_group_results.append(
                SearchResult(
                    url=result.url,
                    title=result.title,
                    raw_content=result.raw_content[:max_chars_per_result] + "..." if len(result.raw_content) > max_chars_per_result else result.raw_content
                )
            )
            result_count += 1
            
        if truncated_group_results:
            truncated_group = SearchResults(
                query=search_result_group.query,
                results=truncated_group_results
            )
            truncated_results.append(truncated_group)

    result_accumulator_system_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(RESULT_ACCUMULATOR_SYSTEM_PROMPT_TEMPLATE),
        HumanMessagePromptTemplate.from_template(template="{search_results}"),
    ])
    result_accumulator_llm = result_accumulator_system_prompt | llm

    rate_limit_delay()
    result = result_accumulator_llm.invoke({**state, "search_results": truncated_results})

    return {"accumulated_content": result.content}


def reflection_feedback_node(
        state: ResearchState, 
        config: RunnableConfig
) -> Command[Literal["final_section_formatter", "query_generator"]]:
    """
    Evaluates the quality and completeness of accumulated research content and determines next steps.
    """
    
    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=configurable.temperature
    )

    reflection_feedback_system_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(REFLECTION_FEEDBACK_SYSTEM_PROMPT_TEMPLATE),
        HumanMessagePromptTemplate.from_template(template="Section: {section}\nAccumulated Content: {accumulated_content}"),
    ])
    reflection_feedback_llm = reflection_feedback_system_prompt | llm

    reflection_count = state["reflection_count"] if "reflection_count" in state else 1
    
    rate_limit_delay()
    result = reflection_feedback_llm.invoke(state)
    
    # Handle different response types from the LLM
    if hasattr(result, 'feedback'):
        feedback = result.feedback
    elif hasattr(result, 'content'):
        feedback = result.content
    else:
        feedback = str(result)

    # Check if feedback indicates content is sufficient
    is_sufficient = False
    if isinstance(feedback, bool):
        is_sufficient = feedback
    elif isinstance(feedback, str):
        is_sufficient = feedback.lower() == "true"
    
    if is_sufficient or (reflection_count >= configurable.num_reflections):
        return Command(
            update={"reflection_feedback": feedback, "reflection_count": reflection_count},
            goto="final_section_formatter"
        )
    else:
        return Command(
            update={"reflection_feedback": feedback, "reflection_count": reflection_count + 1},
            goto="query_generator"
        )


async def final_section_formatter_node(state: ResearchState, config: RunnableConfig):
    """
    Formats the final content for a section of the research report.
    """

    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=configurable.temperature
    )

    final_section_formatter_system_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(FINAL_SECTION_FORMATTER_SYSTEM_PROMPT_TEMPLATE),
        HumanMessagePromptTemplate.from_template(template="Internal Knowledge: {knowledge}\nSearch Result content: {accumulated_content}"),
    ])
    final_section_formatter_llm = final_section_formatter_system_prompt | llm

    rate_limit_delay()
    result =await final_section_formatter_llm.ainvoke(state)
     # --- DB SAVE ---
    run_id = config["configurable"]["run_id"]
    current_section_index = state.get("current_section_index", 0)
    section_name = state['section'].section_name
    await db_manager.add_researched_section(run_id, current_section_index, section_name, result.content)
    # --- END DB SAVE ---

    os.makedirs("logs/section_content", exist_ok=True)

    # Sanitize section name for valid filename
    safe_section_name = re.sub(r'[<>:"/\\|?*]', '', state['section'].section_name)
    safe_section_name = safe_section_name.strip()
    
    with open(f"logs/section_content/{state['current_section_index']+1}. {safe_section_name}.md", "w", encoding="utf-8") as f:
        f.write(f"{result.content}")

    return {"final_section_content": [result.content]}


# async def finalizer_node(state: AgentState, config: RunnableConfig):
#     """
#     Finalizes the research report by generating a conclusion, references, and combining all sections.
#     """

#     configurable = Configuration.from_runnable_config(config)
#     llm = init_llm(
#         provider=configurable.provider,
#         model=configurable.model,
#         temperature=configurable.temperature
#     )

#     extracted_search_results = []
#     for search_results in state['search_results']:
#         for search_result in search_results.results:
#             extracted_search_results.append({"url": search_result.url, "title": search_result.title})

#     finalizer_system_prompt = ChatPromptTemplate.from_messages([
#         SystemMessagePromptTemplate.from_template(FINALIZER_SYSTEM_PROMPT_TEMPLATE),
#         HumanMessagePromptTemplate.from_template(template="Section Contents: {final_section_content}\n\nSearches: {extracted_search_results}"),
#     ])
#     finalizer_llm = finalizer_system_prompt | llm.with_structured_output(ConclusionAndReferences)

#     rate_limit_delay()
#     result =await finalizer_llm.ainvoke({**state, "extracted_search_results": extracted_search_results})

#     # Build the final report
#     company_name = state.get("company_name", "Company")
#     final_report = f"# Risk Assessment Report: {company_name}\n\n"
#     final_report += "\n\n".join([section_content for section_content in state["final_section_content"]])
#     final_report += "\n\n" + result.conclusion
#     final_report += "\n\n# References\n\n" + "\n".join(["- "+reference for reference in result.references])
#         # --- DB FINALIZE ---
#     run_id = config["configurable"]["run_id"]
#     # The result from the LLM (conclusion and references) is saved as the result of this step
#     conclusion_and_refs_dict = {"conclusion": result.conclusion, "references": result.references}
#     await db_manager.finalize_report_run(run_id, final_report, conclusion_and_refs_dict)
#     # --- END DB FINALIZE ---
    
#     os.makedirs("reports", exist_ok=True)  
#     with open(f"reports/{company_name} Risk Assessment Report.md", "w", encoding="utf-8") as f:
#         f.write(final_report)

#     return {"final_report_content": final_report}



async def finalizer_node(state: AgentState, config: RunnableConfig):
    """
    Finalizes the research report by generating risk mitigation recommendations,
    a conclusion, references, and combining all sections.
    """

    configurable = Configuration.from_runnable_config(config)
    llm = init_llm(
        provider=configurable.provider,
        model=configurable.model,
        temperature=configurable.temperature
    )

    # Collect all unique search results with titles and URLs
    all_search_results = {}
    for search_result_group in state.get('search_results', []):
        for result in search_result_group.results:
            if result.url not in all_search_results:
                all_search_results[result.url] = result.title

    # Create a clean list of dictionaries for the prompt
    extracted_search_results = [{"title": title, "url": url} for url, title in all_search_results.items()]

    finalizer_system_prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(FINALIZER_SYSTEM_PROMPT_TEMPLATE),
        HumanMessagePromptTemplate.from_template(template="Section Contents: {final_section_content}\n\nAll Available Sources: {sources_used}"),
    ])
    
    # Use the updated ConclusionAndReferences Pydantic model from struct.py
    finalizer_llm = finalizer_system_prompt | llm.with_structured_output(ConclusionAndReferences)

    print("\nFinalizing report: Generating recommendations, conclusion, and references...")
    rate_limit_delay()
    result = await finalizer_llm.ainvoke({
        "final_section_content": state['final_section_content'],
        "sources_used": json.dumps(extracted_search_results, indent=2)
    })

    # Build the final report using the three new components
    company_name = state.get("company_name", "Company")
    final_report = f"# Risk Assessment Report: {company_name}\n\n"
    
    # Add the main body content (all researched sections)
    final_report += "\n\n".join(state["final_section_content"])
    
    # Add the new, structured final sections from the LLM
    final_report += f"\n\n{result.risk_mitigation_recommendations}"
    final_report += f"\n\n{result.conclusion}"
    final_report += f"\n\n{result.references}"

    # --- DB FINALIZE ---
    run_id = config["configurable"]["run_id"]
    # Save the entire structured result from the LLM
    final_content_dict = result.dict()
    await db_manager.finalize_report_run(run_id, final_report, final_content_dict)
    # --- END DB FINALIZE ---
    
    os.makedirs("reports", exist_ok=True)
    report_filename = f"reports/{company_name.replace(' ', '_')}_Risk_Assessment_Report.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(final_report)
    print(f"\n✓ Final report saved to: {report_filename}")

    return {"final_report_content": final_report}