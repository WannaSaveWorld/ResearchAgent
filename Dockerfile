FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .
RUN useradd --create-home appuser && mkdir /app/data && chown appuser:appuser /app/data
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "researchagent.api:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
