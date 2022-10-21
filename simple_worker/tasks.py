import time
import datetime
from celery import Celery
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from pydub import AudioSegment
from email.message import EmailMessage
import smtplib
import psycopg2

logger = get_task_logger(__name__)

app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

@app.task()
def audio_converter(filename,new_format):
    logger.info('Got Request - Starting work ')
    src = "/simple_worker/data/"+filename
    dst = "/simple_worker/data/"+filename.split(".")[0] + "."+ new_format
    audio = AudioSegment.from_file(src)
    audio.export(dst, format=new_format)
    return "New Format is ready to be downloaded"