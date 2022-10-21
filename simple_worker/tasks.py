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
def get_info_user(userid):
    logger.info('Conection to DB')
    conn = psycopg2.connect(host=os.environ['DATABASE_HOST'],
                            database="user",
                            user=os.environ['DATABASE_USER'],
                            port=5342,
                            password=os.environ['DATABASE_PASSWORD'])
    cur = conn.cursor()
    cur.execute("SELECT username, email FROM users WHERE id = %s", (userid,))
    info = cur.fetchone()
    cur.close()
    logger.info('Info User, OK')    
    return info


@app.task()
def send_email(mail, username,filename):
    logger.info('Got Request - Starting work ')
    From = os.environ['FROM_EMAIL']
    To = os.environ['TO_EMAIL']
    message = "¡Hola " + str(username) + ", la conversión del archivo "+ filename + " está lista para descargar!"
    email = EmailMessage()
    email["From"] = From
    email["To"] = mail
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
    
@app.task()
def upload_status(filename):
    logger.info('Conection to DB')
    conn = psycopg2.connect(host=os.environ['DATABASE_HOST'],
                            database=os.environ['DATABASE_DB'],
                            user=os.environ['DATABASE_USER'],
                            port=os.environ['DATABASE_PORT'],
                            password=os.environ['DATABASE_PASSWORD'])
    cur = conn.cursor()
    cur.execute("UPDATE task SET status=(%s)"
                " WHERE filename = (%s)", ("processed",filename,));
    conn.commit()
    cur.close()
    logger.info('Updated task status')
    return "Status updated"