ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}

RUN apt-get update \
    && apt-get install -y software-properties-common \
    && apt-get install -y python3-launchpadlib \
    && add-apt-repository ppa:alex-p/tesseract-ocr5 \
    && apt-get -y install tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr-jpn \
    tesseract-ocr-script-jpan

RUN pip install uv \
    && apt-get -y install \
    libopencv-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./pyproject.toml ./pyproject.toml
COPY ./requirements.lock ./requirements.lock
COPY ./requirements-dev.lock ./requirements-dev.lock
COPY ./README.md ./README.md
RUN uv pip install --no-cache --system -r requirements.lock

COPY ./src ./src
COPY ./api ./api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--reload", "--host", "0.0.0.0"]
