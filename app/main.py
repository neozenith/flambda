from fastapi import FastAPI
from mangum import Mangum
from app.routes.v1.api import router as api_routes

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(api_routes, prefix="/api/v1")
handler = Mangum(app)
