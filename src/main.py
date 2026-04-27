from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.challenges.router import router as challenges_router
from src.modules.doctors.router import router as doctors_router
from src.modules.patients.router import router as patients_router
from src.modules.restaurants.router import router as restaurants_router
from src.modules.social.router import router as social_router
from src.modules.users.router import router as users_router

app = FastAPI(
    title="Yalla - Backend API",
    description="API pour la plateforme de prévention et de gestion du diabète Yalla",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(challenges_router, prefix="/api/challenges", tags=["challenges"])
app.include_router(social_router, prefix="/api/social", tags=["social"])
app.include_router(restaurants_router, prefix="/api/restaurants", tags=["restaurants"])
app.include_router(doctors_router, prefix="/api/doctors", tags=["doctors"])
app.include_router(patients_router, prefix="/api/patients", tags=["patients"])


@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yalla"}
