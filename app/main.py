"""FastAPI application for AI Support Router."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.schemas import (
    CompareResponse,
    HealthResponse,
    RootResponse,
    RoutingResponse,
    SupportRequest,
)
from app.routers.jev_router import get_jev_router
from app.routers.llm_router import get_llm_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    logger.info("Starting AI Support Router...")
    yield
    logger.info("Shutting down AI Support Router...")
    # Cleanup
    try:
        llm_router = get_llm_router()
        await llm_router.close()
    except:
        pass
    try:
        jev_router = get_jev_router()
        await jev_router.close()
    except:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-style experiment comparing typed AI decision routing "
        "(Jev by TypeSafe AI) with traditional LLM-based routing."
    ),
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/ui")
async def ui():
    """Serve the web UI."""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    return {"error": "UI not found"}


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    """Root endpoint with project information."""
    return RootResponse(
        name=settings.APP_NAME,
        description=(
            "This project demonstrates the difference between using a specialized "
            "decision model (Jev) and a traditional LLM for support ticket routing. "
            "It compares latency, accuracy, and developer experience."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=settings.APP_VERSION)


@app.post("/route/jev", response_model=RoutingResponse)
async def route_with_jev(request: SupportRequest) -> RoutingResponse:
    """Route support request using Jev (TypeSafe AI).
    
    This endpoint uses Jev's structured decision primitive to classify
    the support request into one of the predefined categories.
    
    Args:
        request: Support request containing customer message.
        
    Returns:
        Routing decision with category, probability, and workflow.
        
    Raises:
        HTTPException: If routing fails or API is not configured.
    """
    try:
        router = get_jev_router()
        return await router.route(request)
    except RuntimeError as e:
        logger.error(f"Jev routing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in Jev routing: {e}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@app.post("/route/llm", response_model=RoutingResponse)
async def route_with_llm(request: SupportRequest) -> RoutingResponse:
    """Route support request using traditional LLM.
    
    This endpoint uses a traditional LLM with structured output to classify
    the support request. This represents the baseline approach.
    
    Args:
        request: Support request containing customer message.
        
    Returns:
        Routing decision with category and workflow.
        
    Raises:
        HTTPException: If routing fails or API is not configured.
    """
    try:
        router = get_llm_router()
        return await router.route(request)
    except RuntimeError as e:
        logger.error(f"LLM routing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in LLM routing: {e}")
        raise HTTPException(status_code=500, detail=f"Routing failed: {str(e)}")


@app.post("/route/compare", response_model=CompareResponse)
async def compare_routers(request: SupportRequest) -> CompareResponse:
    """Compare both routing approaches side-by-side.
    
    This endpoint runs both Jev and LLM routers on the same request
    and returns both results for comparison.
    
    Args:
        request: Support request containing customer message.
        
    Returns:
        Comparison response with both routing results.
        
    Raises:
        HTTPException: If either routing approach fails.
    """
    try:
        jev_router = get_jev_router()
        llm_router = get_llm_router()
        
        # Run both routers
        jev_result = await jev_router.route(request)
        llm_result = await llm_router.route(request)
        
        return CompareResponse(
            input=request.message,
            jev=jev_result,
            llm=llm_result,
        )
    except RuntimeError as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
