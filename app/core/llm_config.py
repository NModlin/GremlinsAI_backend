# app/core/llm_config.py
"""
Local LLM Configuration Module for GremlinsAI

This module provides configuration and initialization for various local LLM providers
including Ollama, Hugging Face Transformers, and other local inference servers.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LLAMACPP = "llamacpp"
    MOCK = "mock"

class LLMConfig:
    """Configuration class for LLM providers."""
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.model_name = self._get_model_name()
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
    def _detect_provider(self) -> LLMProvider:
        """Auto-detect the best available LLM provider."""
        # Check for OpenAI API key first
        if os.getenv("OPENAI_API_KEY"):
            return LLMProvider.OPENAI
            
        # Check for Ollama
        if os.getenv("OLLAMA_BASE_URL") or self._check_ollama_available():
            return LLMProvider.OLLAMA
            
        # Check for Hugging Face
        if os.getenv("USE_HUGGINGFACE") == "true":
            return LLMProvider.HUGGINGFACE
            
        # Default to mock for development
        logger.warning("No LLM provider configured, using mock provider")
        return LLMProvider.MOCK
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available on the default port."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_model_name(self) -> str:
        """Get the model name based on provider."""
        provider_models = {
            LLMProvider.OPENAI: os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            LLMProvider.OLLAMA: os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            LLMProvider.HUGGINGFACE: os.getenv("HF_MODEL", "microsoft/DialoGPT-medium"),
            LLMProvider.LLAMACPP: os.getenv("LLAMACPP_MODEL", "llama-2-7b-chat.gguf"),
            LLMProvider.MOCK: "mock-model"
        }
        return provider_models.get(self.provider, "default-model")

def create_llm(config: Optional[LLMConfig] = None):
    """
    Create an LLM instance based on the configuration.
    
    Args:
        config: LLM configuration. If None, auto-detects the best provider.
        
    Returns:
        LLM instance compatible with LangChain
    """
    if config is None:
        config = LLMConfig()
    
    logger.info(f"Initializing LLM with provider: {config.provider}, model: {config.model_name}")
    
    try:
        if config.provider == LLMProvider.OPENAI:
            return _create_openai_llm(config)
        elif config.provider == LLMProvider.OLLAMA:
            return _create_ollama_llm(config)
        elif config.provider == LLMProvider.HUGGINGFACE:
            return _create_huggingface_llm(config)
        elif config.provider == LLMProvider.LLAMACPP:
            return _create_llamacpp_llm(config)
        else:
            logger.warning(f"Provider {config.provider} not implemented, using mock")
            return _create_mock_llm(config)
            
    except Exception as e:
        logger.error(f"Failed to initialize {config.provider} LLM: {e}")
        logger.info("Falling back to mock LLM")
        return _create_mock_llm(config)

def _create_openai_llm(config: LLMConfig):
    """Create OpenAI LLM instance."""
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )

def _create_ollama_llm(config: LLMConfig):
    """Create Ollama LLM instance."""
    try:
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=config.model_name,
            base_url=config.base_url,
            temperature=config.temperature,
            num_predict=config.max_tokens
        )
    except ImportError:
        logger.error("langchain-ollama not installed. Install with: pip install langchain-ollama")
        raise

def _create_huggingface_llm(config: LLMConfig):
    """Create Hugging Face LLM instance."""
    try:
        from langchain_huggingface import HuggingFacePipeline
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            config.model_name,
            device_map="auto",
            torch_dtype="auto"
        )
        
        # Create pipeline
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=config.max_tokens,
            temperature=config.temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        return HuggingFacePipeline(pipeline=pipe)
        
    except ImportError:
        logger.error("Hugging Face dependencies not installed. Install with: pip install transformers accelerate")
        raise

def _create_llamacpp_llm(config: LLMConfig):
    """Create LlamaCpp LLM instance."""
    try:
        from langchain_community.llms import LlamaCpp
        
        model_path = os.getenv("LLAMACPP_MODEL_PATH", f"./models/{config.model_name}")
        
        return LlamaCpp(
            model_path=model_path,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            n_ctx=4096,  # Context window
            verbose=False
        )
    except ImportError:
        logger.error("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        raise

def _create_mock_llm(config: LLMConfig):
    """Create a mock LLM for development/testing."""
    from langchain_core.language_models.fake import FakeListLLM
    
    responses = [
        "I'm a mock AI assistant. I can help you with various tasks, but I'm not connected to a real language model.",
        "This is a simulated response from the GremlinsAI system. In a real deployment, this would be powered by a local LLM.",
        "Mock response: I understand your query and would provide a helpful response if connected to a real language model.",
        "Development mode: This response is generated by a mock LLM for testing purposes."
    ]
    
    return FakeListLLM(responses=responses)

# Global LLM configuration instance
llm_config = LLMConfig()

def get_llm():
    """Get the configured LLM instance."""
    return create_llm(llm_config)

def get_llm_info() -> Dict[str, Any]:
    """Get information about the current LLM configuration."""
    return {
        "provider": llm_config.provider.value,
        "model_name": llm_config.model_name,
        "temperature": llm_config.temperature,
        "max_tokens": llm_config.max_tokens,
        "base_url": llm_config.base_url if llm_config.provider == LLMProvider.OLLAMA else None,
        "available": llm_config.provider != LLMProvider.MOCK
    }
