from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import documents, comparison, annotations, export, auth, chat
from config import get_settings
from database.connection import init_db, close_db, db_is_healthy

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="Policy & Document Comparison Assistant",
    description="AI-powered policy document comparison with semantic analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(comparison.router, prefix="/api/comparison", tags=["Comparison"])
app.include_router(annotations.router,  prefix="/api/annotations",  tags=["Annotations"])
app.include_router(export.router,  prefix="/api/export",  tags=["Export"])
app.include_router(auth.router,  prefix="/api/auth",  tags=["Authentication"])
app.include_router(chat.router,  prefix="/api/chat",  tags=["Chat"])

@app.get("/health", tags=["Health"])
async def health_check():
    db_status = await db_is_healthy()
    response = {
        "status": "ok",
        "service": "Policy Comparison API",
        "version": "1.0.0",
        "database": {
            "status": "ok" if db_status.get("ok") else "error",
            "error": db_status.get("error"),
        },
    }
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
