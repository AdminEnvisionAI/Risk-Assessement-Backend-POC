from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_groq import ChatGroq
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Global rate limiter
last_api_call_time = 0
MIN_TIME_BETWEEN_CALLS = 0.3  # seconds between API calls

def rate_limit_delay():
    """Enforce a minimum delay between API calls to avoid rate limits"""
    global last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - last_api_call_time
    
    if time_since_last_call < MIN_TIME_BETWEEN_CALLS:
        sleep_time = MIN_TIME_BETWEEN_CALLS - time_since_last_call
        time.sleep(sleep_time)
    
    last_api_call_time = time.time()

def init_llm(
        provider: Literal["google"],
        model: str,
        temperature: float = 0.5,
):
    """
    Initialize and return a language model chat interface based on the specified provider.
    """
    provider = provider.lower().strip()

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set. Please set it in your environment variables.")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")
