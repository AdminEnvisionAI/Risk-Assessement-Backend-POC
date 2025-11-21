# Advanced Risk Assessment & Deep Research System

A powerful multi-agent system that combines deep risk parameter discovery with comprehensive research capabilities to generate detailed company risk assessment reports.

## 🎯 Overview

This system integrates two powerful approaches:
1. **Risk Parameter Discovery** (from main.py) - 3-agent system for identifying and assessing company-specific risks
2. **Deep Research** (original deep-research) - Iterative research system with reflection loops

## 🏗️ System Architecture

### Phase 1: Risk Assessment (3 Agents)
```
Company Name Input
    ↓
[Schema Designer] → Identifies risk parameters specific to the company
    ↓
[Risk Assessor] → Assesses each parameter with evidence (LOW/MEDIUM/HIGH/UNKNOWN)
    ↓
[Report Validator] → Validates and formats the risk assessment
```

### Phase 2: Deep Research (Research Agent)
```
[Report Structure Planner] → Creates outline based on risk parameters
    ↓
[Section Formatter] → Breaks down into research sections
    ↓
[Research Agent Loop] → For each section:
    - Generate knowledge
    - Create search queries
    - Search with Tavily
    - Accumulate results
    - Reflect on quality
    - Format final content
    ↓
[Finalizer] → Generate conclusion, references, and complete report
```

## 🚀 Key Features

### Risk Assessment Phase
- **Deep Thinking Prompts**: Highly detailed, systematic prompts with structured analysis
- **Self-Validation**: Agents challenge their own work for quality
- **Evidence-Based**: Every risk rating must cite real sources
- **Dynamic Schema**: Risk parameters tailored to each company's unique profile
- **External vs Internal**: Categorizes risks by locus of control

### Research Phase
- **Iterative Research**: Reflection loops improve content quality
- **Rate Limiting**: Built-in delays to avoid API limits
- **Comprehensive Search**: Multiple queries per section with Tavily
- **Quality Control**: Reflection agent validates content completeness

## 📋 Requirements

```bash
pip install langchain-core langchain-google-genai langgraph tavily-python python-dotenv
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with:
```
GOOGLE_API_KEY=your_google_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### Configurable Parameters (in main.py)
```python
thread = {
    "configurable": {
        "max_queries": 3,          # Max search queries per section
        "search_depth": 3,         # Max results per query
        "num_reflections": 3,      # Max reflection iterations
        "temperature": 0.7,        # LLM temperature for research
        "section_delay_seconds": 5 # Delay between sections
    }
}
```

## 🎮 Usage

### 1. Edit the Company Name
Open `main.py` and change the company name:
```python
COMPANY_NAME = "Tesla Inc"  # Change this to any company
```

### 2. Run the System
```bash
python main.py
```

### 3. Provide Feedback
When prompted:
- Type `continue` to proceed with the report structure
- Or provide feedback to revise the structure

## 📂 Output Files

The system generates several output files:

### Risk Assessment Outputs
- `logs/risk_schema.json` - Identified risk parameters
- `logs/risk_assessment.json` - Risk ratings with evidence
- `logs/validated_risk_report.json` - Final validated assessment

### Research Outputs
- `logs/sections_raw.txt` - Raw section structure
- `logs/sections.json` - Parsed sections
- `logs/section_content/*.md` - Individual section content
- `logs/agent_logs.txt` - Complete execution log

### Final Report
- `reports/[Company Name] Risk Assessment Report.md` - Complete report with:
  - Risk category analyses
  - Evidence and reasoning
  - Risk mitigation recommendations
  - Conclusion
  - References

## 🔧 Customization

### Adjust Risk Assessment Detail
The risk assessment prompts are in `deep_research/risk_prompts.py`:
- `SCHEMA_SYSTEM_PROMPT` - Controls risk parameter identification
- `ASSESS_SYSTEM_PROMPT` - Controls risk assessment process
- `VALIDATOR_SYSTEM_PROMPT` - Controls report validation

### Adjust Research Detail
The research prompts are in `deep_research/prompts.py`:
- `SECTION_KNOWLEDGE_SYSTEM_PROMPT_TEMPLATE`
- `QUERY_GENERATOR_SYSTEM_PROMPT_TEMPLATE`
- `RESULT_ACCUMULATOR_SYSTEM_PROMPT_TEMPLATE`
- etc.

## 📊 Example Output Structure

```
Tesla Inc Risk Assessment Report
│
├── 1. Strategic Risks
│   ├── Market Competition Analysis
│   ├── Technology Disruption Risk
│   └── Business Model Evolution
│
├── 2. Operational Risks
│   ├── Supply Chain Resilience
│   ├── Manufacturing Capacity
│   └── Quality Control
│
├── 3. Financial Risks
│   ├── Leverage Analysis
│   ├── Liquidity Position
│   └── Cost Structure
│
├── 4. Regulatory & Compliance
│   ├── Environmental Regulations
│   ├── Safety Standards
│   └── International Compliance
│
├── Risk Mitigation Recommendations
├── Conclusion
└── References
```

## 🎓 Understanding the Prompts

### Schema Designer Prompt Style
```
═══════════════════════════════════════════════════════════════
PHASE 1: DEEP COMPANY UNDERSTANDING
═══════════════════════════════════════════════════════════════

STEP 1.1 — Initial Hypothesis Formation
• Before searching, ask yourself:
  - What industry/sector does this company likely operate in?
  ...
```

This structured, thinking-first approach ensures:
- Systematic analysis
- Self-validation
- Quality over speed
- Evidence-based decisions

## 🐛 Troubleshooting

### Rate Limiting Errors
- Increase `section_delay_seconds` in config
- Reduce `max_queries` per section
- Check Tavily API quota

### JSON Parsing Errors
- Check logs/agent_logs.txt for raw output
- Ensure .env variables are set correctly
- Verify API keys are valid

### Missing Dependencies
```bash
pip install --upgrade langchain-core langchain-google-genai langgraph tavily-python python-dotenv
```

## 📝 Notes

- **API Costs**: Uses Google Gemini and Tavily APIs - monitor usage
- **Execution Time**: Full report generation takes 10-30 minutes depending on company complexity
- **Quality vs Speed**: The system prioritizes quality through multiple iterations
- **Human Feedback**: Allows review of report structure before deep research begins

## 🔮 Future Enhancements

- [ ] Support for multiple LLM providers (Claude, GPT-4, etc.)
- [ ] Web interface for easier use
- [ ] Batch processing for multiple companies
- [ ] Custom risk frameworks (COSO, ISO 31000, etc.)
- [ ] Export to PDF, Word, PowerPoint
- [ ] Integration with financial databases
- [ ] Real-time monitoring and alerts

## 📄 License

This is a research and educational tool. Ensure compliance with API terms of service and data usage policies.

## 🤝 Contributing

Feel free to enhance the prompts, add new agent capabilities, or improve the research algorithms!

---

**Built with ❤️ using LangGraph, LangChain, and advanced prompt engineering**
