FROM python:3
RUN apt-get update && apt-get install -y ffmpeg

# layer caching for faster builds
COPY requirements.txt /
RUN pip install -r /requirements.txt

#COPY app.py /app.py
ADD . /simple_worker
RUN mkdir -m 777 /simple_worker/data
WORKDIR /simple_worker

ENTRYPOINT python3 worker.py