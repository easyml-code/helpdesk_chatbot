from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from database.client import run_query
from database.utils import pg_escape
from logs.log import logger
from config import settings
import uuid
import time


class ChatSessionManager:
    """Manages chat sessions and enforces limits"""
    
    def __init__(
        self,
        max_context_multiplier: int = 10,
        llm_context_limit: int = 8000,
        session_timeout_minutes: int = 5,
        auto_save_interval_minutes: int = 3
    ):
        self.max_tokens_per_chat = max_context_multiplier * llm_context_limit
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.auto_save_interval = timedelta(minutes=auto_save_interval_minutes)
        self.pending_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.last_save_time: Dict[str, datetime] = {}
        
    def generate_chat_id(self) -> str:
        """Generate unique chat ID"""
        return f"chat_{uuid.uuid4().hex[:16]}"
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{uuid.uuid4().hex[:16]}"
    
    async def get_or_create_chat(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing chat or create new one based on topic"""
        
        # Check for existing active chat with same topic
        query = f"""
        SELECT chat_id, topic, total_tokens, created_at
        FROM chats
        WHERE user_id = '{pg_escape(user_id)}'
        AND is_active = true
        ORDER BY updated_at DESC
        LIMIT 5;
        """
        
        try:
            existing_chats = await run_query(query, access_token, refresh_token)
            
            # If topic matches recent chat and under token limit, reuse it
            if topic and existing_chats:
                for chat in existing_chats:
                    if (chat.get('topic') == topic and 
                        chat.get('total_tokens', 0) < self.max_tokens_per_chat):
                        logger.info(f"Reusing chat {chat['chat_id']} for topic: {topic}")
                        return {
                            'chat_id': chat['chat_id'],
                            'is_new': False,
                            'total_tokens': chat.get('total_tokens', 0)
                        }
            
            # Create new chat
            chat_id = self.generate_chat_id()
            insert_query = f"""
            INSERT INTO chats (chat_id, user_id, topic, total_tokens, is_active, created_at, updated_at)
            VALUES (
                '{chat_id}',
                '{pg_escape(user_id)}',
                {f"'{pg_escape(topic)}'" if topic else 'NULL'},
                0,
                true,
                NOW(),
                NOW()
            )
            RETURNING chat_id;
            """
            
            await run_query(insert_query, access_token, refresh_token)
            logger.info(f"Created new chat {chat_id} for user {user_id}")
            
            return {
                'chat_id': chat_id,
                'is_new': True,
                'total_tokens': 0
            }
            
        except Exception as e:
            logger.error(f"Error in get_or_create_chat: {e}")
            raise
    
    async def check_token_limit(
        self,
        chat_id: str,
        access_token: str,
        refresh_token: str
    ) -> bool:
        """Check if chat has exceeded token limit"""
        
        query = f"""
        SELECT total_tokens
        FROM chats
        WHERE chat_id = '{pg_escape(chat_id)}';
        """
        
        result = await run_query(query, access_token, refresh_token)
        
        if result and len(result) > 0:
            total_tokens = result[0].get('total_tokens', 0)
            if total_tokens >= self.max_tokens_per_chat:
                logger.warning(f"Chat {chat_id} exceeded token limit: {total_tokens}/{self.max_tokens_per_chat}")
                return False
        
        return True
    
    def add_pending_message(
        self,
        chat_id: str,
        session_id: str,
        role: str,
        content: str,
        tokens: int
    ):
        """Add message to pending queue"""
        
        if chat_id not in self.pending_messages:
            self.pending_messages[chat_id] = []
        
        self.pending_messages[chat_id].append({
            'session_id': session_id,
            'role': role,
            'content': content,
            'tokens': tokens,
            'timestamp': datetime.utcnow()
        })
        
        logger.info(f"Added pending message for chat {chat_id}, queue size: {len(self.pending_messages[chat_id])}")
    
    async def should_auto_save(self, chat_id: str) -> bool:
        """Check if auto-save interval has passed"""
        
        if chat_id not in self.last_save_time:
            return True
        
        time_since_save = datetime.utcnow() - self.last_save_time[chat_id]
        return time_since_save >= self.auto_save_interval
    
    async def save_pending_messages(
        self,
        chat_id: str,
        access_token: str,
        refresh_token: str,
        force: bool = False
    ) -> int:
        """Save pending messages to database"""
        
        if chat_id not in self.pending_messages or not self.pending_messages[chat_id]:
            return 0
        
        # Check if should save
        if not force and not await self.should_auto_save(chat_id):
            return 0
        
        messages = self.pending_messages[chat_id]
        total_tokens = sum(msg['tokens'] for msg in messages)
        
        try:
            # Insert messages
            values = []
            for msg in messages:
                values.append(
                    f"('{chat_id}', '{msg['session_id']}', '{pg_escape(msg['role'])}', "
                    f"'{pg_escape(msg['content'])}', {msg['tokens']}, '{msg['timestamp'].isoformat()}')"
                )
            
            insert_query = f"""
            INSERT INTO messages (chat_id, session_id, role, content, tokens, created_at)
            VALUES {', '.join(values)};
            """
            print("insert_query: ", insert_query)
            await run_query(insert_query, access_token, refresh_token)
            print("insert_query: ", insert_query)
            # Update chat total tokens
            update_query = f"""
            UPDATE chats
            SET total_tokens = total_tokens + {total_tokens},
                updated_at = NOW()
            WHERE chat_id = '{chat_id}';
            """
            
            await run_query(update_query, access_token, refresh_token)
            
            # Clear pending messages
            saved_count = len(messages)
            self.pending_messages[chat_id] = []
            self.last_save_time[chat_id] = datetime.utcnow()
            
            logger.info(f"Saved {saved_count} messages for chat {chat_id}, total tokens: {total_tokens}")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error saving messages for chat {chat_id}: {e}")
            raise
    
    async def load_chat_history(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Load all chats for a user"""
        
        query = f"""
        SELECT 
            c.chat_id,
            c.topic,
            c.total_tokens,
            c.is_active,
            c.created_at,
            c.updated_at,
            COUNT(m.message_id) as message_count
        FROM chats c
        LEFT JOIN messages m ON c.chat_id = m.chat_id
        WHERE c.user_id = '{pg_escape(user_id)}'
        GROUP BY c.chat_id, c.topic, c.total_tokens, c.is_active, c.created_at, c.updated_at
        ORDER BY c.updated_at DESC
        LIMIT {limit};
        """
        
        try:
            chats = await run_query(query, access_token, refresh_token)
            logger.info(f"Loaded {len(chats)} chats for user {user_id}")
            return chats
        except Exception as e:
            logger.error(f"Error loading chat history: {e}")
            return []
    
    async def load_chat_messages(
        self,
        chat_id: str,
        access_token: str,
        refresh_token: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Load messages for a specific chat"""
        
        query = f"""
        SELECT 
            message_id,
            session_id,
            role,
            content,
            tokens,
            created_at
        FROM messages
        WHERE chat_id = '{pg_escape(chat_id)}'
        ORDER BY created_at ASC
        LIMIT {limit};
        """
        
        try:
            messages = await run_query(query, access_token, refresh_token)
            logger.info(f"Loaded {len(messages)} messages for chat {chat_id}")
            return messages
        except Exception as e:
            logger.error(f"Error loading messages for chat {chat_id}: {e}")
            raise
    
    async def end_session(
        self,
        chat_id: str,
        access_token: str,
        refresh_token: str
    ):
        """End session and save all pending messages"""
        
        await self.save_pending_messages(chat_id, access_token, refresh_token, force=True)
        logger.info(f"Session ended for chat {chat_id}")


# Global instance
chat_manager = ChatSessionManager(
    session_timeout_minutes=getattr(settings, 'SESSION_TIMEOUT_MINUTES', 5),
    auto_save_interval_minutes=getattr(settings, 'AUTO_SAVE_INTERVAL_MINUTES', 3)
)