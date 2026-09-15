import asyncio
import sys
import os

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.api.database import AsyncSessionLocal, async_engine, Base
from apps.api.routers.simulation import seed_data, run_demo_scenario

async def main():
    print("==================================================================")
    print("  AI-Powered Autonomous E-Commerce Operations Platform - Demo Seed")
    print("==================================================================")
    print("1. Creating database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("2. Seeding baseline products, orders, campaigns, and tickets...")
    async with AsyncSessionLocal() as session:
        await seed_data(session)
        print("3. Executing Demo Scenario (SKU: RUN-SHOE-BLK-42)...")
        demo_res = await run_demo_scenario(session)
        print("Result:", demo_res["message"])
        print("Specialist Agents Executed:", demo_res["agents_executed"])
        print("Proposals Generated:", demo_res["actions_generated"])
        print("------------------------------------------------------------------")
        for res in demo_res["results"]:
            print(f"[{res['agent'].upper()}] (Confidence: {res['confidence']*100:.0f}%, Risk: {res['risk'].upper()})")
            print(f"  Summary: {res['summary']}")
            print(f"  Actions: {res['actions']}")
            print()

    print("Demo Seeding Completed Successfully!")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(main())
