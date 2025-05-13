FROM python:3.12-slim AS builder

SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install --no-install-recommends -y git wget \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && wget -qO- https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /build
COPY pyproject.toml ./
RUN uv pip install --target /tmp/site-packages --requirements pyproject.toml

FROM python:3.12-slim

# Install expat to get libexpat.so.1, which is required by rasterio.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install --no-install-recommends -y expat \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ARG WORKDIR=/work
WORKDIR ${WORKDIR}
COPY --from=builder /tmp/site-packages ./
COPY hls_vi_historical/ ./hls_vi_historical/

# Set PYTHONPATH to WORKDIR because that's where we just copied all of the site
# packages from the builder image.  This allows the console scripts to find the
# necessary dependencies without having to move them to wherever the system
# site packages live.
ENV PYTHONPATH=${WORKDIR}

CMD [ "python", "hls_vi_historical/main.py" ]
