from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import auth, profile, ai_coach, plans, progress, supplements


def create_app() -> FastAPI:
    app = FastAPI(title="OwnCoach AI API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health / keep-alive endpoint ──────────────────────────────────────
    # The mobile app pings this every 10 minutes to prevent Render from sleeping.
    @app.get("/health", tags=["health"])
    async def health_check():
        return JSONResponse({"status": "ok", "service": "OwnCoach API"})

    # Root also returns health so any ping works
    @app.get("/", tags=["health"])
    async def root():
        return JSONResponse({"status": "ok", "service": "OwnCoach API"})

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(profile.router, prefix="/profile", tags=["profile"])
    app.include_router(ai_coach.router, prefix="/ai", tags=["ai"])
    app.include_router(plans.router, prefix="/plans", tags=["plans"])
    app.include_router(progress.router, prefix="/progress", tags=["progress"])
    app.include_router(supplements.router, prefix="/supplements", tags=["supplements"])

    return app


app = create_app()
