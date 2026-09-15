import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from apps.api.database import async_engine, Base
from apps.api.routers import (
    health, auth, dashboard, approvals, agents, inventory, orders, tickets, pricing, simulation, products
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ecom_ai_platform")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down ecom-ai-platform control plane.")

app = FastAPI(
    title="AI-Powered Autonomous E-Commerce Operations Platform",
    description="Control plane API and Multi-Agent decision engine for e-commerce operations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(pricing.router, prefix="/api/v1")
app.include_router(simulation.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")

# Mount built web dashboard assets if present
web_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "dist"))
if os.path.exists(web_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(web_dist_path, "assets")), name="assets")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(os.path.join(web_dist_path, "index.html"))

    @app.get("/dashboard")
    async def serve_dashboard_alias():
        return FileResponse(os.path.join(web_dist_path, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "platform": "AI-Powered Autonomous E-Commerce Operations Platform",
            "status": "online",
            "api_docs": "/docs",
            "version": "1.0.0"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=True)
