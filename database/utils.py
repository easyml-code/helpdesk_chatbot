from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from supabase import Client
from logs.log import logger
from pydantic import BaseModel
from typing import Tuple
import traceback

async def get_new_tokens(supabase: Client, refresh_token: str):
    if not refresh_token:
        logger.warning("get_new_tokens called without refresh_token")
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        # Supabase Python SDK is sync — run it in threadpool to avoid blocking
        refresh_response = await run_in_threadpool(supabase.auth.refresh_session, refresh_token)

        if not getattr(refresh_response, "session", None):
            logger.info("Invalid refresh token or no session returned")
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        new_access_token = refresh_response.session.access_token
        new_refresh_token = refresh_response.session.refresh_token

        if not new_access_token or not new_refresh_token:
            logger.error("Refresh returned incomplete tokens: %s", refresh_response)
            raise HTTPException(status_code=500, detail="Failed to refresh tokens")

        logger.info("Refreshed tokens for session (uid=%s)", getattr(refresh_response.session.user, "id", "unknown"))
        return new_access_token, new_refresh_token

    except HTTPException:
        raise

    except Exception as exc:
        tb = traceback.format_exc()
        logger.exception("Unexpected error while refreshing tokens: %s", tb)
        raise HTTPException(status_code=500, detail="Unexpected error while refreshing session")
    
def pg_escape(value: str) -> str:
    return value.replace("'", "''")
