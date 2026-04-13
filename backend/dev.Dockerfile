FROM python:3.11-slim-bookworm
ARG USER=ubuntu
ARG UID=1000

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --uid ${UID} ${USER} --home /home/${USER}
WORKDIR /app
RUN chown -R ${UID}:${UID} /app
USER ${UID}

RUN pip3 install "uv>=0.4.12"
ENV PATH="/home/${USER}/.local/bin:${PATH}"
ENV UV_PROJECT_ENVIRONMENT="/home/${USER}/.venv"

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project --no-editable