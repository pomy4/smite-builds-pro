FROM python:3.12.7-slim-bookworm

RUN useradd guest --user-group --create-home --shell /bin/bash
WORKDIR /app

COPY requirements.txt ./
RUN pip install --requirement requirements.txt --root-user-action ignore

ENV PYTHONUNBUFFERED=1
RUN mkdir storage && chown guest:guest storage
COPY run.sh ./
COPY backend backend
COPY static static
USER guest

CMD ["./run.sh", "start_docker_full"]
