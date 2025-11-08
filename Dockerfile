ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.5.13 /uv /uvx /bin/

WORKDIR /app
COPY ./pyproject.toml ./pyproject.toml
COPY ./uv.lock ./uv.lock
COPY ./README.md ./README.md
RUN uv sync --frozen --no-dev

COPY ./src ./src
COPY ./api ./api

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0"]
