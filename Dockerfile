# Intentionally vulnerable MCP server with FAKE data. Never expose to the internet.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAB_DATA_DIR=/data \
    MCP_MODE=safe

WORKDIR /srv

# Install the package (and its dependencies) from the source files
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Unprivileged user; /data is where the fake data is generated on first start
# (nothing is baked into the image). Mount a volume there, or let it be temporary.
RUN useradd --system --uid 10001 appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000

# The mode is chosen at run time (MCP_MODE=safe|vulnerable). The default is safe.
CMD ["python", "-m", "ai_assistant_mcp_server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
