# Runs the agent + eval suite in a sealed box: the mock world ships inside the
# image, and the agent can't touch the host filesystem.
#
#   docker compose run --rm bench run -c configs/baseline.yaml --trials 4
#
# Models are served by Ollama outside the container (OLLAMA_URL). On macOS run
# Ollama natively: Docker on Mac has no GPU access.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home bench \
    && git config --system --add safe.directory '*'

# The venv lives outside /app so bind-mounting the repo for development doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock README.md .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY benchmark ./benchmark
COPY configs ./configs
RUN uv sync --frozen --no-dev && mkdir -p runs && chown -R bench /app

# No .git inside the image, so record the commit it was built from.
ARG GIT_SHA=unknown
ENV PYAGI_GIT_SHA=$GIT_SHA \
    OLLAMA_URL=http://host.docker.internal:11434

USER bench
ENTRYPOINT ["uv", "run", "--no-sync", "bench"]
CMD ["--help"]
