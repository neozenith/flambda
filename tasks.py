# Standard Library
import shutil
from pathlib import Path

# Third Party
from invoke import task
from invoke_common_tasks import format, init_config, lint, typecheck  # noqa

# Our Libraries
from app.core.auth import get_password_hash


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

    # install deps
    print(f"DEPS: {out_dir_base}/requirements.in -> {out_dir_base}")
    context.run(f"poetry export --without-hashes -o {out_dir_base}/requirements.in")
    context.run(
        f"python3 -m pip install --target {out_dir_base} -r {out_dir_base}/requirements.in --ignore-installed -qq"
    )

    # TODO: Tidy this up so multiple lambdas can be built in parallel with this function
    shutil.make_archive(f"./dist/{target}", "zip", f"./{out_dir_base}")


@task
def dev(c):
    """Start a FastAPI dev server."""
    c.run("uvicorn app.main:app --reload", pty=True)


@task
def clean(c):
    """Clean up artifacts."""
    print("Removing build and dist...")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)
    print("Cleaning notebook outputs.")
    c.run("jupyter nbconvert --ClearOutputPreprocessor.enabled=True --clear-output notebooks/*.ipynb")


@task
def build_lambda(c):
    """Build the lambda function specified. Default: app."""
    _build_lambda(c, "app")


@task
def hash_password(c, password):
    print(get_password_hash(password))


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
