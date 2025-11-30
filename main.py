from database.client import get_access_token, run_query
from config import settings
from fastapi import HTTPException
from supabase import create_client, Client
import jwt
import os

if __name__ == "__main__":
    import asyncio

    async def test():
        email = settings.VENDOR_EMAIL
        password = settings.VENDOR_PASSWORD
        query = "select count(*) from invoices;"

        access_token, refresh_token = await get_access_token(email, password)

        rows = await run_query(query, access_token, refresh_token)
        print("\n\nQuery Result:", rows)
        print("Database client module test completed.")

    asyncio.run(test())