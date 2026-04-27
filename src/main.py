from fastapi import FastAPI
from src.modules.users.router import router as users_router
from src.modules.challenges.router import router as challenges_router
from src.modules.social.router import router as social_router
from src.modules.restaurants.router import router as restaurants_router

app = FastAPI(
    title="Yalla - Backend API",
    description="API pour le réseau social de santé Yalla",
    version="1.0.0"
)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(challenges_router, prefix="/api/challenges", tags=["challenges"])
app.include_router(social_router, prefix="/api/social", tags=["social"])
app.include_router(restaurants_router, prefix="/api/restaurants", tags=["restaurants"])

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yalla"}
