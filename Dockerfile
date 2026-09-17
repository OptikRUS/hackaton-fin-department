FROM astral/uv:python3.14-trixie-slim AS builder

ENV UV_PROJECT_ENVIRONMENT=/project/.venv

WORKDIR /project

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --all-extras --no-install-project

FROM astral/uv:python3.14-trixie-slim

ENV CUSTOM_USER=python-user
ENV APP_PATH=/project
ENV PYTHONPATH=$APP_PATH/
ENV PATH=/project/.venv/bin:${PATH}
ENV UV_CACHE_DIR=/project/.cache/uv
ENV APP_ADDRESS=0.0.0.0
ENV APP_PORT=8080

RUN groupadd $CUSTOM_USER && useradd -g $CUSTOM_USER $CUSTOM_USER \
    && mkdir -p $APP_PATH && chown -R $CUSTOM_USER:$CUSTOM_USER $APP_PATH

WORKDIR $APP_PATH

RUN apt-get update && apt-get -y install make --no-install-recommends

COPY --from=builder /project/.venv ./.venv
COPY . ./
USER $CUSTOM_USER:$CUSTOM_USER

EXPOSE 8080

CMD ["uv", "run", "python", "src/main.py"]
