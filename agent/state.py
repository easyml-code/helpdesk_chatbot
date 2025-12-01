from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from operator import add


class AgentState(TypedDict):
    """State for the agent graph"""
    messages: Annotated[Sequence[BaseMessage], add]
    chat_id: str
    session_id: str
    user_id: str
    current_topic: str | None
    total_tokens: int
    session_start_time: float