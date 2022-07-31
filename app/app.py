# Standard Library
import io
import os
from typing import Union

# Third Party
import awswrangler as wr
import boto3
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mangum import Mangum

from .core.auth import redirect_to_login, exchange_oauth2_code

#  from app.routes.v1.api import router as api_routes

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

boto3_session = None
if os.getenv("AWS_PROFILE", None) is not None:
    # Local dev uses profile by name
    boto3_session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"), region_name=os.getenv("AWS_REGION"))
else:
    # Deployed lambda uses injected variables
    boto3_session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION"),
    )


@app.get("/vis/{model}", response_class=HTMLResponse)
async def vis(request: Request, model: str, auth_token: Union[str, None] = Cookie(default=None)):
    database = "finances"
    query = """
        SELECT
            date_format(tx_date, '%Y-%m') as timebucket
            , rule_based_label as category
            , sum(amount) as amount
            , count(1) as transactions
        FROM
            finances.silver_labelled
        WHERE rule_based_label in ('Groceries', 'Takeaway/Fastfood', 'Cafe', 'Fuel', 'Health/Pharmacy')
        GROUP BY 1, 2
        ORDER BY 1 DESC, 2 DESC, 4 ASC
    """

    df = wr.athena.read_sql_query(query, database, boto3_session=boto3_session)
    fig = px.line(df, x="timebucket", y="amount", color="category")
    buffer = io.StringIO()
    fig.write_html(buffer)
    return buffer.getvalue().encode()


@app.get("/")
async def root(request: Request):
    return {"message": "Hello"}


@app.get("/auth")
async def get_auth(request: Request, response: Response, code: str = None):
    if code:
        token = await exchange_oauth2_code(code)
        print(token)
        return token


@app.get(
    "/{model}",
    response_class=HTMLResponse,
)
async def model_routes(request: Request, model: str):
    if "Authorization" not in request.headers:
        return redirect_to_login()
    return templates.TemplateResponse("index.html", {"request": request, "model": model})


#  app.include_router(api_routes, prefix="/api/v1")
handler = Mangum(app)
