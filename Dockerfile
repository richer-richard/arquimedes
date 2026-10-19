FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md glama.json ./
COPY arquimedes ./arquimedes
COPY tools ./tools
COPY data/index.json ./data/index.json
COPY problems/aops ./problems/aops
COPY problems/cemc ./problems/cemc

RUN pip install --no-cache-dir . \
    && useradd --create-home app \
    && chown -R app:app /app

USER app

CMD ["arquimedes-mcp"]
