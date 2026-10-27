FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.15-slim@sha256:f786b2e19cf9bb54e96bfcd4c1b40c4c56336c22e60607ffd4b080ae5b5dee83 AS dependencies

ARG APP_VERSION=0.0.0+unknown
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SEASONAL_VCAPTCHA=${APP_VERSION}

WORKDIR /build
COPY --from=uv /uv /uvx /bin/
COPY requirements.txt .
COPY pyproject.toml README.md ./
COPY lib ./lib
RUN uv pip install --prefix=/install --no-cache -r requirements.txt \
    && uv pip install --prefix=/install --no-cache --no-deps .

FROM python:3.15-slim@sha256:f786b2e19cf9bb54e96bfcd4c1b40c4c56336c22e60607ffd4b080ae5b5dee83 AS runtime-files

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SEASONAL_VCAPTCHA_CONFIG=/run/config/config.yaml \
    VOSK_MODEL=/opt/seasonal-vcaptcha/models/model-small-en-us

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 sox \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 vcaptcha \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin vcaptcha \
    && install -d -o 10001 -g 10001 -m 0700 /var/lib/seasonal-vcaptcha

WORKDIR /app
COPY --from=dependencies /install /usr/local
RUN chmod -R go-w /app
FROM scratch AS runtime

COPY --from=runtime-files / /
WORKDIR /app
USER 10001:10001
ARG APP_VERSION=0.0.0+unknown
ARG APP_REVISION=unknown
ARG APP_BUILD_DATE=unknown
LABEL org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$APP_REVISION" \
      org.opencontainers.image.created="$APP_BUILD_DATE"
ENTRYPOINT ["/usr/local/bin/python3.15", "-m", "seasonal_vcaptcha.daemon"]
RUN ["/usr/local/bin/python3.15", "-c", "import os; assert os.getuid() == 10001; assert os.stat('/app/lib/seasonal_vcaptcha/daemon.py').st_uid == 0; assert not os.access('/app', os.W_OK)"]
