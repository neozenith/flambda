FROM public.ecr.aws/lambda/python:3.9
RUN python3 -m pip install -U pip poetry
COPY poetry.toml .
COPY pyproject.toml .
RUN poetry lock --no-ansi
RUN poetry install --no-root --only main
RUN ls -la .
# RUN cat requirements.in
# RUN pip3 install -r requirements.in --target "${LAMBDA_TASK_ROOT}" \
#         --implementation cp \
#         --only-binary=:all: \
#         --upgrade
COPY .venv/lib/python3.9/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY app/ ${LAMBDA_TASK_ROOT}/app/
RUN ls -la ${LAMBDA_TASK_ROOT}
CMD [ "app.app.handler" ]
