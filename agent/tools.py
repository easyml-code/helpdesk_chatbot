from langchain_core.tools import tool
from typing import List, Dict, Any, Annotated
from logs.log import logger
from langgraph.prebuilt import InjectedState

@tool
async def get_invoice_details(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Fetch invoice details from the database based on user query
    
    Args:
        query: PostgreSQL Select query or search parameters for invoice details
        state: Injected state from LangGraph containing config
    
    Returns:
        List of invoice records
    """
    try:
        from database.client import run_query
        
        print("\n\n\n\n\n", query, "\n\n\n\n\n")
        # Get tokens from state (passed via config)
        access_token = state.get("config", {}).get("access_token")
        refresh_token = state.get("config", {}).get("refresh_token")
        
        if not access_token:
            logger.error("No access token found in state")
            return []
        
        logger.info(f"🔍 Executing query: {query[:100]}...")
        results = await run_query(
            query=query, 
            access_token=access_token,
            refresh_token=refresh_token
        )
        logger.info(f"Fetched {len(results)} invoice records")
        return f"Found {len(results)} records. Here's the data: {str(results)}"
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}", exc_info=True)
        return "Wrong query."

# List of all tools
TOOLS = [get_invoice_details]