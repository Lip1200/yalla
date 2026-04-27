from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_social():
    return {"module": "social"}
