FROM python:3
RUN apt-get update && apt-get install -y ffmpeg
RUN mkdir /backend
WORKDIR /backend
ADD requirements.txt /backend/
RUN pip install -r requirements.txt
ADD * /backend/
EXPOSE 5000