from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage
from agent.graph import agent_graph
from agent.chat_manager import chat_manager
from agent.state import AgentState
from database.client import get_access_token
from logs.log import logger
from config import settings
import time
import jwt


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    topic: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    chat_id: str
    session_id: str
    is_new_chat: bool


class ChatHistoryResponse(BaseModel):
    chats: List[dict]
    total: int


class MessageHistoryResponse(BaseModel):
    messages: List[dict]
    chat_id: str
    total: int


async def get_user_from_token(access_token: str) -> str:
    """Extract user ID from JWT token"""
    try:
        decoded = jwt.decode(
            access_token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True}
        )
        return decoded.get("sub")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid access token")


@router.post("/auth/login")
async def login(email: str, password: str):
    """Authenticate user and return tokens"""
    try:
        access_token, refresh_token = await get_access_token(email, password)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    access_token: str,
    refresh_token: str
):
    """Send message and get AI response"""
    
    try:
        # Get user ID from token
        user_id = await get_user_from_token(access_token)
        
        # Get or create chat
        chat_info = await chat_manager.get_or_create_chat(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            topic=request.topic
        )
        
        chat_id = chat_info['chat_id']
        is_new_chat = chat_info['is_new']
        
        # Generate session ID
        session_id = chat_manager.generate_session_id()
        
        # Prepare initial state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=request.message)],
            "chat_id": chat_id,
            "session_id": session_id,
            "user_id": user_id,
            "current_topic": request.topic,
            "total_tokens": chat_info.get('total_tokens', 0),
            "session_start_time": time.time()
        }
        
        # Run agent graph
        config = {
            "configurable": {
                "thread_id": chat_id,
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        }
        
        result = await agent_graph.ainvoke(initial_state, config)
        
        # FORCE SAVE IMMEDIATELY after each interaction
        saved_count = await chat_manager.save_pending_messages(
            chat_id, access_token, refresh_token, force=True
        )
        logger.info(f"Force saved {saved_count} messages after chat interaction")
        
        # Extract AI response
        ai_response = result["messages"][-1].content if result["messages"] else "No response generated"
        
        return ChatResponse(
            response=ai_response,
            chat_id=chat_id,
            session_id=session_id,
            is_new_chat=is_new_chat
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    access_token: str,
    refresh_token: str,
    limit: int = 50
):
    """Get all chats for the authenticated user"""
    
    try:
        user_id = await get_user_from_token(access_token)
        
        chats = await chat_manager.load_chat_history(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            limit=limit
        )
        
        return ChatHistoryResponse(
            chats=chats,
            total=len(chats)
        )
        
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{chat_id}/messages", response_model=MessageHistoryResponse)
async def get_chat_messages(
    chat_id: str,
    access_token: str,
    refresh_token: str,
    limit: int = 100
):
    """Get messages for a specific chat"""
    
    try:
        messages = await chat_manager.load_chat_messages(
            chat_id=chat_id,
            access_token=access_token,
            refresh_token=refresh_token,
            limit=limit
        )
        
        return MessageHistoryResponse(
            messages=messages,
            chat_id=chat_id,
            total=len(messages)
        )
        
    except Exception as e:
        logger.error(f"Error loading messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{chat_id}/end")
async def end_chat_session(
    chat_id: str,
    access_token: str,
    refresh_token: str
):
    """End session and save all pending messages"""
    
    try:
        await chat_manager.end_session(
            chat_id=chat_id,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        return {"status": "success", "message": "Session ended and messages saved"}
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))