FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home app
COPY --chown=app:app backend/ /workspace/backend/
COPY --chown=app:app FlexBridge_1_4_schema.sql /workspace/FlexBridge_1_4_schema.sql
COPY --chown=app:app specs/ /workspace/specs/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
