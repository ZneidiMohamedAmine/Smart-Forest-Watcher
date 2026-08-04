FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    DEBIAN_FRONTEND=noninteractive \
    CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /build

RUN apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 update \
    && apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 upgrade -y \
    && apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip "setuptools>=78.1.1" wheel \
    && grep -Ev "^(GDAL @|twisted-iocpsupport==|psycopg2==)" requirements.txt > requirements-linux.txt \
    && python -m pip install --prefix=/install "GDAL==$(gdal-config --version)" \
    && python -m pip install --prefix=/install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && PYTHONPATH=/install/lib/python3.11/site-packages python -m pip install --prefer-binary --prefix=/install -r requirements-linux.txt \
    && python -m pip install --prefix=/install --force-reinstall --no-deps "msgpack==1.2.1"


FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    DEBIAN_FRONTEND=noninteractive \
    IN_DOCKER=1 \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so.32 \
    PATH="/usr/local/bin:$PATH"

WORKDIR /app

RUN apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 update \
    && apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 upgrade -y \
    && apt-get -o Acquire::Retries=10 -o Acquire::http::Timeout=300 -o Acquire::https::Timeout=300 install -y --no-install-recommends \
        libgdal32 \
        libgeos-c1v5 \
        libproj25 \
        libgomp1 \
        libpq5 \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN rm -rf /usr/local/lib/python3.11/site-packages/setuptools* \
    && python -m pip install --upgrade pip wheel \
    && python -m pip install --force-reinstall "setuptools>=78.1.1" "msgpack==1.2.1" \
    && rm -rf /root/.cache/pip

# TEMP DIAGNOSTIC: surface every setuptools/msgpack metadata dir found anywhere
# in the image as a workflow annotation, so it's visible without repo login.
# Remove once the Trivy false-positive/duplicate-install mystery is solved.
RUN echo "::warning::setuptools_dist=$(find / -xdev -iname 'setuptools-*' -path '*dist-info*' 2>/dev/null | paste -sd ';' -)" \
    && echo "::warning::msgpack_dist=$(find / -xdev -iname 'msgpack-*' -path '*dist-info*' 2>/dev/null | paste -sd ';' -)" \
    && echo "::warning::pip_show=$(python -m pip show setuptools msgpack 2>&1 | paste -sd '|' -)"

RUN mkdir -p /app/logs /app/staticfiles /app/img

EXPOSE 8000

CMD ["/usr/local/bin/daphne", "-b", "0.0.0.0", "-p", "8000", "project.asgi:application"]
