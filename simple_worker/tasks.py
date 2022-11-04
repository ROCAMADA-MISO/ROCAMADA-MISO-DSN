import os
import time
from datetime import datetime
import json
from celery import Celery
from celery.utils.log import get_task_logger
from celery.signals import worker_process_init, worker_process_shutdown
from pydub import AudioSegment
import requests
import psycopg2
from google.cloud import storage
import tempfile


logger = get_task_logger(__name__)
redis_host = os.environ['REDIS_HOST']
redis_uri = "redis://{}:6379/0".format(redis_host)
app = Celery('tasks', broker=redis_uri, backend=redis_uri)
db_host = os.environ['DB_HOST']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
bucket_name = os.environ['BUCKET_NAME']

conn = None
conn2 = None

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
    tmpdir = tempfile.gettempdir()
    src = tmpdir + '/' + filename
    dst = tmpdir + '/' + filename.split(".")[0] + "."+ new_format
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
    storage_client = storage.Client()
    bucket_name = bucket_name
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.download_to_filename(src)
    audio = AudioSegment.from_file(src)
    audio.export(dst, format=new_format)
    blob = bucket.blob(filename.split(".")[0] + "."+ new_format)
    blob.upload_from_filename(dst)
    
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
    return "Flag updated"


@app.task()
def get_info_user(userid, filename):
    logger.info('Conection to DB')
    
    cur = conn2.cursor()
    cur.execute('SELECT username, email FROM "user" WHERE id = %s',[userid])
    info = cur.fetchone()
    cur.close()
    logger.info('Info User, OK')    
    send_email.delay(filename, info[1], info[0])
    return info

@app.task()
def send_email(filename, email, username):
    logger.info('Got Request - Starting work ')
    SANDBOX = os.environ['SANDBOX']
    FROM = os.environ['FROM_EMAIL']
    KEY = os.environ['KEY']
    request_url = f'https://api.mailgun.net/v3/{SANDBOX}/messages'
    message = f'Hola {username}, la conversión del archivo {filename} está listo para ser descargado!'
    From = f'{FROM} <postmaster@{SANDBOX}>'
    request = requests.post(request_url,
                            auth=('api', KEY),
                            data={
                                'from': From,
                                'to': email,
                                'subject': 'Correo de notificación',
                                'text': message})
    logger.info('Mail Finished ')
    if request.status_code == 200:
        return 'Email sent!'
    else:
        return 'Something went wrong...' 


@app.task()
def upload_status(filename):
    logger.info('Conection to DB')
    cur = conn.cursor()
    cur.execute("UPDATE task SET status=(%s)"
                " WHERE filename = (%s)", ("processed",filename,));
    cur.execute("UPDATE task SET processed_at=(%s) WHERE filename = (%s)", (datetime.now(), filename))
    conn.commit()
    cur.close()
    logger.info('Updated task status')
    return "Status updated"


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global conn, conn2
    if conn:
        print('Closing database connectionn for worker.')
        conn.close()
        conn2.close()
