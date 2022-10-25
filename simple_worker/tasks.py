import os
import time
import datetime
import json
from celery import Celery
from celery.utils.log import get_task_logger
from celery.signals import worker_process_init, worker_process_shutdown
#from celery.schedules import crontab
from pydub import AudioSegment
from email.message import EmailMessage
import smtplib
import psycopg2


logger = get_task_logger(__name__)
redis_host = os.environ['REDIS_HOST']
redis_uri = "redis://{}:6379/0".format(redis_host)
app = Celery('tasks', broker=redis_uri, backend=redis_uri)
db_host = os.environ['DB_HOST']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']

conn = None
conn2 =None

@worker_process_init.connect
def init_worker(**kwargs):
    global conn, conn2
    print('Initializing database connection for worker.')
    conn = psycopg2.connect(host=db_host,
                            database='tasks',
                            user=db_user,
                            port=5432,
                            password=db_password)
    conn2 = psycopg2.connect(host=db_host,
                            database="users",
                            user=db_user,
                            port=5432,
                            password=db_password)



@app.task()
def audio_converter(filename,new_format,userid,timestamp):
    logger.info('Got Request - Starting work ')
    start = timestamp
    done = time.time()
    elapsed = done - start
    if elapsed/60 > 10:
        update_flag.delay()
        return logger.info('Task took too long to complete '+ str(elapsed/60))
    src = "/simple_worker/data/"+filename
    dst = "/simple_worker/data/"+filename.split(".")[0] + "."+ new_format
    audio = AudioSegment.from_file(src)
    audio.export(dst, format=new_format)
    if os.environ['EMAIL_SEND'] == 'True':
        msn = get_info_user.delay(userid, filename)
    upload_status.delay(filename)
    return "New Format is ready to be downloaded"
    

@app.task()
def update_flag():
    cur = conn.cursor()
    cur.execute("UPDATE flag SET exceeded = true")
    conn.commit()
    cur.close()
    #conn.close()
    return "Flag updated"


@app.task()
def get_info_user(userid, filename):
    logger.info('Conection to DB')
    
    cur = conn2.cursor()
    cur.execute('SELECT username, email FROM "user" WHERE id = %s',[userid])
    info = cur.fetchone()
    cur.close()
    #conn.close()
    logger.info('Info User, OK')    
    send_email.delay(filename, info[1], info[0])
    return info

@app.task()
def send_email(filename, email, username):
    logger.info('Got Request - Starting work ')
    From = os.environ['FROM_EMAIL']
    To = email
    message = "¡Hola " + str(username) + ", la conversión del archivo "+ filename + " está listo para descargar!"
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
    
@app.task()
def upload_status(filename):
    logger.info('Conection to DB')
    cur = conn.cursor()
    cur.execute("UPDATE task SET status=(%s)"
                " WHERE filename = (%s)", ("processed",filename,));
    conn.commit()
    cur.close()
    #conn.close()
    logger.info('Updated task status')
    return "Status updated"


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global conn, conn2
    if conn:
        print('Closing database connectionn for worker.')
        conn.close()
        conn2.close()
