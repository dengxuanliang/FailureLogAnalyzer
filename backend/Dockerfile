FROM registry.access.redhat.com/ubi9/python-311:latest
USER 0

ARG APP_USER=fla
ARG APP_UID=1000
ARG APP_GID=1000

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV HOME=/home/${APP_USER}

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER}

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --requirement requirements.txt \
    && pip install --no-deps .

COPY . .
RUN mkdir -p /tmp/fla_uploads && \
    chown -R ${APP_USER}:${APP_USER} /app /tmp/fla_uploads

USER ${APP_USER}

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
