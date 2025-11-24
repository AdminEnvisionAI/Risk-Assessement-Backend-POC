from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .state import AgentState, ResearchState
from .struct import SectionOutput
from .nodes import (
    risk_schema_designer_node,
    risk_assessor_node,
    risk_validator_node,    
    report_structure_planner_node,
    human_feedback_node,
    section_formatter_node,
    section_knowledge_node,
    query_generator_node,
    tavily_search_node,
    content_extractor_node,
    result_accumulator_node,
    reflection_feedback_node,
    final_section_formatter_node,
    queue_next_section_node,
    finalizer_node
)


# <<< ----- RESEARCH AGENT (Sub-graph) ----- >>>

research_builder = StateGraph(ResearchState, output=SectionOutput)

research_builder.add_node("section_knowledge", section_knowledge_node)
research_builder.add_node("query_generator", query_generator_node)
research_builder.add_node("tavily_search", tavily_search_node)
research_builder.add_node("content_extractor", content_extractor_node)
research_builder.add_node("result_accumulator", result_accumulator_node)
research_builder.add_node("reflection", reflection_feedback_node)
research_builder.add_node("final_section_formatter", final_section_formatter_node)

research_builder.add_edge(START, "section_knowledge")
research_builder.add_edge("section_knowledge", "query_generator")
research_builder.add_edge("query_generator", "tavily_search")
# research_builder.add_edge("tavily_search", "result_accumulator")
research_builder.add_edge("tavily_search", "content_extractor")
research_builder.add_edge("content_extractor", "result_accumulator")
research_builder.add_edge("result_accumulator", "reflection")
research_builder.add_edge("final_section_formatter", END)



# <<< ----- MAIN AGENT (Integrated Risk Assessment + Deep Research) ----- >>>

memory_saver = MemorySaver()

builder = StateGraph(AgentState)

# Risk Assessment Phase (3 agents)
builder.add_node("risk_schema_designer", risk_schema_designer_node)
builder.add_node("risk_assessor", risk_assessor_node)
builder.add_node("risk_validator", risk_validator_node)

# Deep Research Phase (automated)
builder.add_node("report_structure_planner", report_structure_planner_node)
builder.add_node("queue_next_section", queue_next_section_node)
builder.add_node("research_agent", research_builder.compile())
builder.add_node("finalizer", finalizer_node)

builder.set_entry_point("risk_schema_designer")
builder.add_edge("risk_schema_designer", "risk_assessor")
builder.add_edge("risk_assessor", "risk_validator")
builder.add_edge("risk_validator", "report_structure_planner")
builder.add_edge("report_structure_planner", "queue_next_section")  # Direct to queue
builder.add_edge("research_agent", "queue_next_section")
builder.add_edge("finalizer", END)

agent_graph = builder.compile(checkpointer=memory_saver)
