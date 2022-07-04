# Standard Library
import io

# Third Party
import plotly.express as px
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mangum import Mangum

from .core.auth import authenticate_user

#  from app.routes.v1.api import router as api_routes

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, authenticated: bool = Depends(authenticate_user)):
    #  return templates.TemplateResponse("index.html", {"request": request})

    df = px.data.iris()
    fig = px.scatter(df, x="sepal_width", y="sepal_length", color="petal_length")
    buffer = io.StringIO()
    fig.write_html(buffer)
    return buffer.getvalue().encode()


@app.get("/{model}", response_class=HTMLResponse)
async def model_routes(request: Request, model: str):
    return templates.TemplateResponse("index.html", {"request": request, "model": model})


#  app.include_router(api_routes, prefix="/api/v1")
handler = Mangum(app)
