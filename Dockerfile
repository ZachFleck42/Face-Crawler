FROM python:3.10.5

WORKDIR /app

COPY ./app /app

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip

RUN pip install -r requirements.txt