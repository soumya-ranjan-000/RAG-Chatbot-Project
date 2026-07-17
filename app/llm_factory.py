import os
import json
import logging
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger("rag-chat")

# Resolve settings.json path relative to this file
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def get_persisted_settings() -> dict:
    """Reads settings from settings.json."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read settings file: {e}")
    return {}

def get_llm(temperature: float = 0.1, streaming: bool = True) -> BaseChatModel:
    """
    Returns a LangChain ChatModel instance based on the active environment and service provider in settings.json.
    
    Supports:
    - env: "local" or "prod"
    - local_service_provider: "LMStudio" (or Llama placeholder)
    - prod_service_provider: "openai" (or anthropic, gemini placeholders)
    """
    settings = get_persisted_settings()
    env = settings.get("env", "prod").lower()

    if env == "local":
        provider = settings.get("local_service_provider", "LMStudio")
        model_name = settings.get("local_model", "qwen2.5-7b-instruct")
        
        logger.info(f"LLM Factory: Initializing local LLM. Provider: {provider}, Model: {model_name}")

        if provider == "LMStudio":
            api_base = settings.get("lmstudio_api_base") or os.environ.get("LMSTUDIO_API_BASE") or "http://localhost:1234/v1"
            from langchain_openai import ChatOpenAI
            
            # LM Studio is OpenAI-compatible. We route requests to the LM Studio base URL.
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                base_url=api_base,
                api_key="lm-studio",  # Placeholder key as LangChain's ChatOpenAI requires it
                streaming=streaming,
                stream_options={"include_usage": True} if streaming else None,
                timeout=600.0,  # 10 minutes timeout to prevent disconnections during local prompt processing
                stream_chunk_timeout=0  # Disable chunk timeout to allow slow pre-fill times
            )
        elif provider == "Llama":
            # Placeholder for Llama. In a production local scenario, this might connect
            # to a local Llama.cpp, Ollama, or vLLM instance.
            raise NotImplementedError(
                f"Local provider '{provider}' is not fully implemented yet. "
                "Please configure 'LMStudio' as your local service provider."
            )
        else:
            raise ValueError(f"Unsupported local service provider: {provider}")

    else:  # prod
        provider = settings.get("prod_service_provider", "openai").lower()
        model_name = settings.get("prod_model") or settings.get("model") or "gpt-4o-mini"
        
        logger.info(f"LLM Factory: Initializing prod LLM. Provider: {provider}, Model: {model_name}")

        if provider == "openai":
            key = settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY_TEMP")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=key,
                streaming=streaming,
                stream_options={"include_usage": True} if streaming else None
            )
        elif provider == "anthropic":
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                raise ImportError(
                    "langchain-anthropic package is not installed. "
                    "Please install it using 'pip install langchain-anthropic' to use Anthropic models."
                )
            key = settings.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
            return ChatAnthropic(
                model=model_name,
                temperature=temperature,
                api_key=key,
                streaming=streaming
            )
        elif provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise ImportError(
                    "langchain-google-genai package is not installed. "
                    "Please install it using 'pip install langchain-google-genai' to use Google Gemini models."
                )
            key = settings.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=key,
                streaming=streaming
            )
        else:
            raise ValueError(f"Unsupported production service provider: {provider}")
