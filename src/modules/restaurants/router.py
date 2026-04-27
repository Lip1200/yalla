from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_restaurants():
    return {"module": "restaurants"}
