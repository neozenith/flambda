# Standard Library
import os
import re
import shutil
from pathlib import Path

# Third Party
import boto3
from dotenv import load_dotenv
from invoke import task
from invoke_common_tasks import format, init_config, lint, typecheck  # noqa

load_dotenv()
AWS_REGION = os.getenv("AWS_REGION")
AWS_PROFILE = os.getenv("AWS_PROFILE")
ECR_HOST = os.getenv("ECR_HOST")
ECR_REPO = os.getenv("ECR_REPO")
strip_version_numbers = re.compile("==.*$")


@task
def ecr_login(c):
    c.run(
        f"aws ecr get-login-password --profile {AWS_PROFILE} --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_HOST}"
    )


def _build_lambda(context, target):
    print(f"\nBUILD: {target}")
    out_dir_root = "build"
    src_dir = Path(target)
    out_dir = Path(out_dir_root) / target / target
    out_dir_base = Path(out_dir_root) / target

    if not Path(src_dir).is_dir():
        raise ValueError(f"Could not build '{target}' because missing folder '{src_dir}'")

    print(f"CLEAN: {out_dir}")
    if Path(out_dir).is_dir():
        shutil.rmtree(out_dir, ignore_errors=True)

    print(f"COPY: {src_dir} -> {out_dir}")
    shutil.copytree(src_dir, out_dir)

    requirements_filepath = _export_requirements(context, out_dir_base)
    # install deps
    # https://aws.amazon.com/premiumsupport/knowledge-center/lambda-python-package-compatible/
    context.run(
        f"""python3 -m pip install \
        --target {out_dir_base} \
        -r {requirements_filepath} \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --only-binary=:all: \
        --upgrade \
        --ignore-installed""",
        pty=True,
    )

    # TODO: Tidy this up so multiple lambdas can be built in parallel with this function
    shutil.make_archive(f"./dist/{target}", "zip", f"./{out_dir_base}")
    print(f"./dist/{target}.zip")


def _export_requirements(context, out_dir_base):
    requirements_filepath = f"{out_dir_base}/requirements.in"
    print(f"DEPS: {requirements_filepath} -> {out_dir_base}")
    context.run(f"poetry export --without-hashes -o {requirements_filepath}")
    _strip_version_numbers(requirements_filepath)
    return requirements_filepath


def _strip_version_numbers(filename):
    output = []
    with open(filename, "r") as f:
        for line in f:
            output.append(strip_version_numbers.sub("", line))
    with open(filename, "w") as f:
        f.write("".join(output))


@task
def dev(c):
    """Start a FastAPI dev server."""
    c.run("uvicorn app.app:app --reload", pty=True)


@task
def clean(c):
    """Clean up artifacts."""
    print("Removing build and dist...")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)


@task
def build_lambda_container(c):
    target_name = "app"
    requirements_filepath = _export_requirements(c, target_name)
    print(requirements_filepath)
    c.run(f"docker build --progress plain -t {target_name}:latest .", pty=True)
    c.run(f"docker tag {target_name}:latest {ECR_REPO}:latest", pty=True)


@task
def deploy_lambda_container(c):
    c.run(f"docker push {ECR_REPO}:latest")


@task
def build_lambda(c):
    """Build the lambda function specified. Default: app."""
    _build_lambda(c, "app")


@task
def upload(c, target="app", profile="play", bucket="play-projects-joshpeak", prefix="lambda/code"):
    """Upload artifact to s3."""
    print(f"Upload profile: {profile}")
    session = boto3.Session(profile_name=profile)
    s3_client = session.client("s3")
    src_file = f"./dist/{target}.zip"
    print(f"Uploading: {src_file} --> s3://{bucket}/{prefix}/{target}.zip")
    response = s3_client.upload_file(src_file, bucket, f"{prefix}/{target}.zip")
    print(response)


@task
def lab(c):
    """Startup jupyter lab instance."""
    c.run("jupyter-lab --notebook-dir=notebooks", pty=True)


@task
def publish_notebook(c):
    """Perform a clean run of a notebook with cleared state."""
    print("Cleaning notebook outputs.")
    c.run("jupyter nbconvert --ClearOutputPreprocessor.enabled=True --clear-output notebooks/*.ipynb")
    print("Executing notebooks...")
    c.run("jupyter nbconvert --to notebook --inplace --execute notebooks/*.ipynb")
