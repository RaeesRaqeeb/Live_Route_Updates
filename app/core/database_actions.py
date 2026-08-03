import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

# 1. Use async def for asynchronous database operations
async def deleting_data():

    # 2. Open the async session using a context manager
    async with AsyncSessionLocal() as db_session:

        # 3. Use 'await' for async execution
        await db_session.execute(text('DELETE FROM scrape_results;'))
        await db_session.execute(text('DELETE FROM routes;'))
        await db_session.execute(text('DELETE FROM user_queries;'))
        await db_session.execute(text('DELETE FROM nhmp_closures;'))

    # 4. Use 'await' to commit changes
        await db_session.commit()

    print("Data deleted successfully")


# 5. Run the async function using the asyncio event loop
if __name__ == "__main__":
    asyncio.run(deleting_data())
