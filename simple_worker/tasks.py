import os
import time
import datetime
from celery import Celery
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from pydub import AudioSegment
from email.message import EmailMessage
from dotenv import load_dotenv
import smtplib
import psycopg2

load_dotenv()

logger = get_task_logger(__name__)

app = Celery('tasks', broker=os.environ['REDIS'], backend='redis://redis:6379/0')

@app.task()
def audio_converter(filename,new_format):
    logger.info('Got Request - Starting work ')
    src = "/simple_worker/data/"+filename
    dst = "/simple_worker/data/"+filename.split(".")[0] + "."+ new_format
    audio = AudioSegment.from_file(src)
    audio.export(dst, format=new_format)
    return "New Format is ready to be downloaded"

@app.task()
def send_email(userid):
    logger.info('Got Request - Starting work ')
    From = os.environ['FROM_EMAIL']
    To = os.environ['TO_EMAIL']
    message = "¡Hola " + str(userid) + ", conversión de archivo terminada!"
    email = EmailMessage()
    email["From"] = From
    email["To"] = To
    email["Subject"] = "Correo de notificación"
    email.set_content(message)
    try:
        smtp = smtplib.SMTP_SSL("smtp.gmail.com")
        smtp.login(From, os.environ['EMAIL_PASSWORD'])
        smtp.sendmail(From, To, email.as_string())
        smtp.quit()
        logger.info('Mail Finished ')
        return 'Email sent!'
    except:
        return 'Something went wrong...'  