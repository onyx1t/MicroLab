from fastapi import FastAPI
from app.api.v1 import endpoints
import os

app = FastAPI(
    title="Delivery Microservice",
    docs_url="/docs",
    openapi_url="/openapi.json",
    root_path="/api/v1/delivery"
)

app.include_router(endpoints.router, prefix="", tags=["delivery"])

@app.get("/")
def read_root():
    return {"message": "Delivery Service is Running on port 8003"}

@app.get("/api/v1/delivery/docs", include_in_schema=False,
         summary="Access interactive API documentation")
async def get_api_docs():
    """Redirect to the auto-generated OpenAPI documentation"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")