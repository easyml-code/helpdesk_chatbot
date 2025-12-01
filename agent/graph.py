from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from agent.state import AgentState
from agent.nodes import process_input, generate_response, save_messages, should_continue
from logs.log import logger


def create_agent_graph():
    """Create the agent workflow graph"""
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("save_messages", save_messages)
    
    # Set entry point
    workflow.set_entry_point("process_input")
    
    # Add edges
    workflow.add_edge("process_input", "generate_response")
    workflow.add_edge("generate_response", "save_messages")
    
    # Add conditional edge
    workflow.add_conditional_edges(
        "save_messages",
        should_continue,
        {
            "continue": END,
            "end": END
        }
    )
    
    # Use memory checkpointer for session management
    checkpointer = MemorySaver()
    
    # Compile graph
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Agent graph created successfully")
    return app


# Global graph instance
agent_graph = create_agent_graph()