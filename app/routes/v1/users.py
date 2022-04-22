from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel


class User(BaseModel):
    name: str
    salary: float
    tax: Optional[float] = None


router = APIRouter()


@router.get("/")
async def get_users():
    return {"message": "get Users!"}


@router.post("/")
async def create_user(user: User):
    return user
