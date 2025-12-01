from langchain_groq import ChatGroq
from config import settings
from typing import Optional
from logs.log import logger

class LLMClient:
    """LLM client wrapper for Groq"""
    
    def __init__(self):
        self._llm: Optional[ChatGroq] = None
    
    def get_llm(self) -> ChatGroq:
        """Get or create Groq LLM instance"""
        if self._llm is None:
            self._llm = ChatGroq(
                model=settings.LLM_MODEl,
                groq_api_key=settings.GROQ_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=60.0,
                max_retries=3,
            )
            logger.info(f"llm_initialized - model={settings.LLM_MODEl}, provider=groq")
        
        return self._llm


# Global instance
llm_client = LLMClient()


def get_llm() -> ChatGroq:
    """Dependency for tools and agents"""
    return llm_client.get_llm()