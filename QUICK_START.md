# 🚀 QUICK START GUIDE

Get your advanced risk assessment report in 3 simple steps!

## Step 1: Setup (One-time)

### Install Dependencies
```bash
pip install langchain-core langchain-google-genai langgraph tavily-python python-dotenv
```

### Configure API Keys
The `.env` file is already configured with API keys. If you need to update them:
```
GOOGLE_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
```

## Step 2: Choose Your Company

Edit `main.py` line 8:
```python
COMPANY_NAME = "Tesla Inc"  # ← Change this to any company
```

Examples:
- `"Microsoft Corporation"`
- `"Apple Inc"`
- `"Amazon.com Inc"`
- `"TCS"` (Tata Consultancy Services)

## Step 3: Run!

```bash
python main.py
```

### What Happens Next?

1. **Risk Assessment Phase (5-10 minutes)**
   - ✓ Schema Designer identifies risk parameters
   - ✓ Risk Assessor rates each risk (LOW/MEDIUM/HIGH)
   - ✓ Report Validator formats the assessment

2. **Human Feedback**
   - Review the proposed report structure
   - Type `continue` to proceed OR provide feedback

3. **Deep Research Phase (10-20 minutes)**
   - ✓ System researches each risk category in depth
   - ✓ Multiple search iterations per section
   - ✓ Reflection loops ensure quality

4. **Report Generated! 🎉**
   - Find your report in: `reports/[Company Name] Risk Assessment Report.md`
   - Supporting data in: `logs/` folder

## 📊 Sample Output

```markdown
# Tesla Inc Risk Assessment Report

## 1. Strategic Risks

### Market Competition Analysis
[Detailed analysis with evidence from sources...]

### Technology Disruption Risk
[Research findings with citations...]

## 2. Operational Risks
[...]

## Risk Mitigation Recommendations
[Actionable recommendations...]

## Conclusion
[Executive summary...]

## References
- Source 1
- Source 2
...
```

## ⏱️ Typical Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Risk Assessment | 5-10 min | Identifies and assesses risk parameters |
| Report Planning | 1-2 min | Creates research structure |
| Human Feedback | Variable | You review and approve structure |
| Deep Research | 10-20 min | In-depth research on each category |
| Finalization | 1-2 min | Generates conclusion and references |
| **Total** | **~20-35 min** | Complete risk assessment report |

## 🎛️ Fine-Tuning (Optional)

Want faster results? Edit `main.py` line 23-30:
```python
thread = {
    "configurable": {
        "max_queries": 2,          # Reduce from 3 to 2
        "search_depth": 2,         # Reduce from 3 to 2
        "num_reflections": 2,      # Reduce from 3 to 2
        "section_delay_seconds": 3 # Reduce from 5 to 3
    }
}
```

⚠️ Note: Fewer queries = faster but potentially less comprehensive

## 🆘 Need Help?

### Common Issues

**"API Key Error"**
→ Check `.env` file has valid keys

**"Rate Limit Error"**
→ Increase `section_delay_seconds` to 10

**"JSON Parse Error"**
→ Check `logs/agent_logs.txt` for details

### Still Stuck?
Check the full `README.md` for detailed troubleshooting.

---

**That's it! You're ready to generate professional risk assessment reports! 🎯**
