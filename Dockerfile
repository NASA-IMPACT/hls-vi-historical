FROM python:3.12 AS builder

ENV UV_INSTALL_DIR=/home/.local/bin
WORKDIR /build
SHELL [ "/bin/bash", "-o", "pipefail", "-c" ]

RUN apt-get update \
    && apt-get install --no-install-recommends -y git tar \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | env INSTALLER_NO_MODIFY_PATH=1 UV_INSTALL_DIR="${UV_INSTALL_DIR}" sh

COPY pyproject.toml uv.lock ./
RUN "${UV_INSTALL_DIR}"/uv pip install --target /tmp/site-packages --requirements pyproject.toml

FROM public.ecr.aws/lambda/python:3.12

# Install expat to get libexpat.so.1, which is required by rasterio (indirectly?)
RUN dnf -y update \
    && dnf -y install expat \
    && dnf clean all

COPY --from=builder /tmp/site-packages "${LAMBDA_TASK_ROOT}"
COPY lambda_function.py "${LAMBDA_TASK_ROOT}"/

CMD [ "lambda_function.handler" ]
