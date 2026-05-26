from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.modules.auth.router import router as auth_router
from src.modules.challenges.router import router as challenges_router
from src.modules.consents.router import router as consents_router
from src.modules.doctors.router import router as doctors_router
from src.modules.health.router import router as health_router
from src.modules.messaging.router import router as messaging_router
from src.modules.patients.router import router as patients_router
from src.modules.restaurants.router import router as restaurants_router
from src.modules.social.router import router as social_router
from src.modules.users.router import router as users_router

app = FastAPI(
    title="Yalla - Backend API",
    description="API pour la plateforme de prévention et de gestion du diabète Yalla",
    version="1.0.0",
)

# Dynamically parse permitted origins from settings
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(consents_router, prefix="/api/consents", tags=["consents"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(messaging_router, prefix="/api/messaging", tags=["messaging"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(challenges_router, prefix="/api/challenges", tags=["challenges"])
app.include_router(social_router, prefix="/api/social", tags=["social"])
app.include_router(restaurants_router, prefix="/api/restaurants", tags=["restaurants"])
app.include_router(doctors_router, prefix="/api/doctors", tags=["doctors"])
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])


@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yalla"}
