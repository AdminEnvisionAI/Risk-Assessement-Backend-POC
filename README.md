
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

### 1. Run the System
```bash
python main.py
```
