from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_challenges():
    return {"module": "challenges"}
