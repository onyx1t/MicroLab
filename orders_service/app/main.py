from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.api.v1 import endpoints
import os

# Определяем REPLICA_ID прямо в main.py
REPLICA_ID = os.getenv("REPLICA_ID", "default-instance")

app = FastAPI(
    title="Orders Microservice",
    docs_url="/docs",
    openapi_url="/openapi.json",
    root_path="/api/v1/orders"
)

@app.middleware("http")
async def add_replica_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Replica-ID"] = REPLICA_ID
    return response

# Включение роутов
app.include_router(endpoints.router, prefix="", tags=["orders"])


@app.get("/")
def read_root():
    return {"message": f"Orders Service {REPLICA_ID} is Running on port 8001"}


@app.get("/api/v1/orders/docs", include_in_schema=False,
         summary="Access interactive API documentation")
async def get_api_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
