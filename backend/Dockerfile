FROM registry.access.redhat.com/ubi9/python-311:latest

USER 0

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --requirement requirements.txt \
    && pip install --no-deps .

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
