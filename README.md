# Flambda: FastAPI + Lambda Function URLs

Quick and easy services running a FastAPI service on an AWS Lambda FunctionURL for rapid prototyping.

## Getting Started

To get the dev environment and tooling setup, you'll want to make sure you're virtual env
is in the same directory as this project then start a _shell_ to activate the virtual env.

```sh
poetry config virtualenvs.in-project true
poetry shell
poetry install

# Update dependencies
poetry lock && poetry install
```

## Development

Running a local dev instance is simply running a FastAPI server

```sh
inv dev
# OR
uvicorn app.main:app --reload
```

During execution on Lambda we use [Mangum](https://mangum.io) (not Magnum, MAN GUM...) as a wrapper over our normally long running instance of FastAPI to become a single shot handler of Lambda HTTP requests.

## Deployment

Deployment is a few steps as we will need to:
 - Copy all source code to a `build` directory
 - Generate a `requirements.in` file from our `pyproject.toml` 
 - `pip install` these requirements in the root of the build directory with the copied source code
 - Zip up this build directory as an archive and save to `dist` as this is the final package to upload
 - TODO: Upload to S3
 - TODO: Create / update the lambda definition with the new code archive

```sh
inv deploy
```

