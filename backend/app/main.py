# Apply patches before any other imports
import os
import sys

# Disable ChromaDB telemetry via environment variables
os.environ["CHROMA_TELEMETRY_OFF"] = "True"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_IMPL"] = ""

# Disable tiktoken parallelism to avoid crashes
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# Patch posthog before chromadb imports it
try:
    import posthog

    posthog.disabled = True

    def _noop(*args, **kwargs):
        return None

    # Patch module-level capture
    posthog.capture = _noop

    # Patch Posthog class methods
    if hasattr(posthog, "Posthog"):
        posthog.Posthog.capture = lambda *args, **kwargs: None
        posthog.Posthog._enqueue = lambda *args, **kwargs: None

except ImportError:
    pass

# Now we can safely import the rest of the application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import (
    auth,
    papers,
    ai_models,
    conversations,
    reports,
    batch_operations,
    search,
    health,
    admin,
    users,
    translate,
    folders,
)
from app.core.exceptions import setup_exception_handlers

app = FastAPI(
    title="Online Paper Reader API",
    description="Support AI reading, management, translation, search",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(ai_models.router, prefix="/api/models", tags=["Models"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Chat"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(batch_operations.router, prefix="/api/batch", tags=["Batch"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(users.router, prefix="/api/users", tags=["Personalization"])
app.include_router(translate.router, prefix="/api/translate", tags=["Translate"])
app.include_router(folders.router, prefix="/api/folders", tags=["Folders"])


@app.get("/")
async def root():
    return {"message": "Welcome to Online Paper Reader API", "version": "2.2.0"}
