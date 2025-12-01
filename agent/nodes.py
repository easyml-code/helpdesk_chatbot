from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent.state import AgentState
from langchain_core.runnables import RunnableConfig
from agent.llm import get_llm
from agent.chat_manager import chat_manager
from logs.log import logger
from typing import Dict, Any
import time


async def process_input(state: AgentState, config: RunnableConfig) -> AgentState:
    """Process user input and check limits"""
    
    access_token = config.get("configurable", {}).get("access_token")
    refresh_token = config.get("configurable", {}).get("refresh_token")
    
    chat_id = state.get("chat_id")
    
    # Check token limit
    if chat_id:
        within_limit = await chat_manager.check_token_limit(
            chat_id, access_token, refresh_token
        )
        
        if not within_limit:
            state["messages"].append(
                AIMessage(content="This chat has reached its maximum length. Please start a new chat to continue.")
            )
            return state
    
    logger.info(f"Processing input for chat {chat_id}")
    return state

async def generate_response(state: AgentState, config: RunnableConfig) -> AgentState:
    """Generate AI response using LLM"""
    
    llm = get_llm()
    messages = state["messages"]
    
    # Add system message if first message in this interaction
    full_messages = list(messages)
    if len(full_messages) == 1:
        system_msg = SystemMessage(
            content="You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
        )
        full_messages = [system_msg] + full_messages
    
    try:
        # Invoke LLM
        response = await llm.ainvoke(full_messages)
        
        # Add AI response to messages
        ai_message = AIMessage(content=response.content)
        state["messages"].append(ai_message)
        
        # Get the actual user message content
        user_msg_content = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_msg_content = msg.content
                break
        
        ai_msg_content = response.content
        
        # Estimate tokens (rough approximation: 1 token ≈ 0.75 words)
        estimated_user_tokens = int(len(user_msg_content.split()) * 1.33)
        estimated_ai_tokens = int(len(ai_msg_content.split()) * 1.33)
        total_estimated = estimated_user_tokens + estimated_ai_tokens
        
        state["total_tokens"] = state.get("total_tokens", 0) + total_estimated
        
        # Add to pending messages
        chat_manager.add_pending_message(
            chat_id=state["chat_id"],
            session_id=state["session_id"],
            role="user",
            content=user_msg_content,
            tokens=estimated_user_tokens
        )
        
        chat_manager.add_pending_message(
            chat_id=state["chat_id"],
            session_id=state["session_id"],
            role="assistant",
            content=ai_msg_content,
            tokens=estimated_ai_tokens
        )
        
        logger.info(f"Generated response for chat {state['chat_id']}, tokens: {total_estimated}")
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        state["messages"].append(
            AIMessage(content="I apologize, but I encountered an error. Please try again.")
        )
    return state

async def generate_response1(state: AgentState, config: RunnableConfig) -> AgentState:
    """Generate AI response using LLM"""
    
    llm = get_llm()
    messages = state["messages"]
    
    # Add system message if first message
    if len([m for m in messages if isinstance(m, (HumanMessage, AIMessage))]) == 1:
        system_msg = SystemMessage(
            content="You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
        )
        messages = [system_msg] + list(messages)
    
    try:
        # Invoke LLM
        response = await llm.ainvoke(messages)
        
        # Add AI response to messages
        ai_message = AIMessage(content=response.content)
        state["messages"].append(ai_message)
        
        # Estimate tokens (rough approximation)
        user_msg = messages[-1].content if messages else ""
        ai_msg = response.content
        
        estimated_tokens = len(user_msg.split()) + len(ai_msg.split())
        state["total_tokens"] = state.get("total_tokens", 0) + estimated_tokens
        
        # Add to pending messages
        chat_manager.add_pending_message(
            chat_id=state["chat_id"],
            session_id=state["session_id"],
            role="user",
            content=user_msg,
            tokens=len(user_msg.split())
        )
        
        chat_manager.add_pending_message(
            chat_id=state["chat_id"],
            session_id=state["session_id"],
            role="assistant",
            content=ai_msg,
            tokens=len(ai_msg.split())
        )
        
        logger.info(f"Generated response for chat {state['chat_id']}, tokens: {estimated_tokens}")
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        state["messages"].append(
            AIMessage(content="I apologize, but I encountered an error. Please try again.")
        )
    
    return state


async def save_messages(state: AgentState, config: RunnableConfig) -> AgentState:
    """Auto-save messages if interval has passed"""
    
    access_token = config.get("configurable", {}).get("access_token")
    refresh_token = config.get("configurable", {}).get("refresh_token")
    chat_id = state.get("chat_id")
    
    if chat_id:
        try:
            saved = await chat_manager.save_pending_messages(
                chat_id, access_token, refresh_token, force=False
            )
            if saved > 0:
                logger.info(f"Auto-saved {saved} messages for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error auto-saving messages: {e}")
    
    return state


def should_continue(state: AgentState) -> str:
    """Determine if conversation should continue"""
    
    messages = state["messages"]
    
    # Check if last message indicates chat limit reached
    if messages and isinstance(messages[-1], AIMessage):
        if "reached its maximum length" in messages[-1].content:
            return "end"
    
    return "continue"