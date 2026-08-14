from fastapi import APIRouter

from app.api.v1.endpoints import auth, bots, admin, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(bots.router)
api_router.include_router(admin.router)
