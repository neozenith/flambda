from invoke import task
from invoke_common_tasks import format, lint, typecheck, init_config  # noqa

import os
import glob
import shutil
from pathlib import Path


def _build_lambda(context, target):
    print(f"\nBUILD: {target}")
    src_dir = Path(target)
    out_dir = Path("dist") / target

    if not Path(src_dir).is_dir():
        raise ValueError(f"Could not build '{target}' because missing folder '{src_dir}'")

    print(f"CLEAN: {out_dir}")
    if Path(out_dir).is_dir():
        shutil.rmtree(out_dir, ignore_errors=True)

    print(f"COPY: {src_dir} -> {out_dir}")
    shutil.copytree(src_dir, out_dir)

    # install deps
    print(f"DEPS: {src_dir}/requirements.txt -> {out_dir}")
    context.run("poetry export --without-hashes -o requirements.in")
    context.run(f"python3 -m pip install --target dist -r requirements.in --ignore-installed -qq")


@task
def clean(c):
    print("Removing dist...")
    shutil.rmtree("dist", ignore_errors=True)
    targets = ["./requirements.in"] + glob.glob("outputs.*")
    for f in targets:
        print(f"Removing {f}...")
        if Path(f).exists():
            os.remove(f)


@task
def build_lambda(c):
    _build_lambda(c, "app")
    shutil.make_archive("output", "zip", "./dist")
