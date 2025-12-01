import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict
import time


# Configuration
API_BASE_URL = "http://localhost:8000/api"  # Adjust as needed


def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def login(email: str, password: str):
    """Authenticate user"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            params={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.refresh_token = data["refresh_token"]
            st.session_state.authenticated = True
            return True
        else:
            st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False


def load_chat_history():
    """Load all chats for the user"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/chat/history",
            params={
                "access_token": st.session_state.access_token,
                "refresh_token": st.session_state.refresh_token,
                "limit": 50
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.chat_history = data["chats"]
        else:
            st.error("Failed to load chat history")
    except Exception as e:
        st.error(f"Error loading chat history: {str(e)}")


def load_chat_messages(chat_id: str):
    """Load messages for a specific chat"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/chat/{chat_id}/messages",
            params={
                "access_token": st.session_state.access_token,
                "refresh_token": st.session_state.refresh_token,
                "limit": 100
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in data["messages"]
            ]
            st.session_state.current_chat_id = chat_id
        else:
            st.error("Failed to load messages")
    except Exception as e:
        st.error(f"Error loading messages: {str(e)}")


def send_message(message: str, topic: str = None):
    """Send message to chatbot"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "chat_id": st.session_state.current_chat_id,
                "topic": topic
            },
            params={
                "access_token": st.session_state.access_token,
                "refresh_token": st.session_state.refresh_token
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.current_chat_id = data["chat_id"]
            
            # Add messages to session
            st.session_state.messages.append({"role": "user", "content": message})
            st.session_state.messages.append({"role": "assistant", "content": data["response"]})
            
            return True
        else:
            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return False


def end_session():
    """End current chat session"""
    if st.session_state.current_chat_id:
        try:
            requests.post(
                f"{API_BASE_URL}/chat/{st.session_state.current_chat_id}/end",
                params={
                    "access_token": st.session_state.access_token,
                    "refresh_token": st.session_state.refresh_token
                }
            )
        except Exception as e:
            st.error(f"Error ending session: {str(e)}")


def main():
    st.set_page_config(
        page_title="AI Chatbot",
        page_icon="🤖",
        layout="wide"
    )
    
    init_session_state()
    
    # Login screen
    if not st.session_state.authenticated:
        st.title("🤖 AI Chatbot - Login")
        
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if login(email, password):
                    st.success("Login successful!")
                    load_chat_history()
                    st.rerun()
        return
    
    # Main chat interface
    st.title("🤖 AI Chatbot")
    
    # Sidebar - Chat History
    with st.sidebar:
        st.header("Chat History")
        
        if st.button("🔄 Refresh History"):
            load_chat_history()
        
        if st.button("➕ New Chat"):
            st.session_state.current_chat_id = None
            st.session_state.messages = []
            st.rerun()
        
        if st.button("🚪 Logout"):
            end_session()
            st.session_state.clear()
            st.rerun()
        
        st.divider()
        
        # Display chat history
        for chat in st.session_state.chat_history:
            chat_id = chat.get("chat_id")
            topic = chat.get("topic", "Untitled")
            message_count = chat.get("message_count", 0)
            updated_at = chat.get("updated_at", "")
            
            # Format date
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%b %d, %H:%M")
            except:
                date_str = "Unknown"
            
            # Chat button
            if st.button(
                f"💬 {topic[:20]}{'...' if len(topic) > 20 else ''}\n📅 {date_str} | 💬 {message_count}",
                key=chat_id,
                use_container_width=True
            ):
                load_chat_messages(chat_id)
                st.rerun()
    
    # Main chat area
    st.header("Chat")
    
    # Display current chat info
    if st.session_state.current_chat_id:
        st.caption(f"Chat ID: {st.session_state.current_chat_id}")
    else:
        st.caption("New Chat - Start a conversation!")
    
    # Display messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(content)
            elif role == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(content)
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Show user message immediately
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.write(user_input)
        
        # Get topic if new chat
        topic = None
        if not st.session_state.current_chat_id:
            # Simple topic extraction (first 50 chars of message)
            topic = user_input[:50]
        
        # Send message and get response
        with st.spinner("Thinking..."):
            if send_message(user_input, topic):
                # Show assistant response
                with chat_container:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(st.session_state.messages[-1]["content"])
                
                # Reload chat history to update sidebar
                load_chat_history()
                st.rerun()


if __name__ == "__main__":
    main()