import os
import sys
import time
import psycopg2
import requests
import tempfile
from datetime import datetime
from pydub import AudioSegment
from concurrent import futures
from google.cloud import storage
from google.cloud import pubsub_v1
from io import BytesIO

print("Starting worker")
sys.stdout.flush()

db_host = os.environ['DB_HOST']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
project_id = "miso-nubes-g14"
subscription_id = "audio-processing-sub"
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

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

print("Worker started")
sys.stdout.flush()


def callback(message):
    message.ack()
    print("Received file ", message.attributes['filename'])
    sys.stdout.flush()
    audio_converter(message.attributes['filename'],
                    message.attributes['new_format'], int(
                        message.attributes['user_id']),
                    datetime.strptime(message.attributes['timestamp'], '%Y-%m-%d %H:%M:%S'))


def audio_converter(filename, new_format, userid, timestamp):
    bucket_name = 'audio_converter_g14'
    start = timestamp.timestamp()
    done = time.time()
    elapsed = done - start
    if elapsed/60 > 10:
        update_flag()
        print('Task took too long to complete ' + str(elapsed/60))
        sys.stdout.flush()
        return
    src = 'https://storage.googleapis.com/{}/{}'.format(bucket_name, filename)
    res = requests.get(src)
    audio = AudioSegment.from_file(BytesIO(res.content))
    tmpdir = tempfile.gettempdir()
    dst = tmpdir + '/' + filename.split(".")[0] + "." + new_format

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    audio.export(dst, format=new_format)
    blob = bucket.blob(filename.split(".")[0] + "." + new_format)
    blob.upload_from_filename(dst)
    os.remove(dst)

    if os.environ['EMAIL_SEND'] == 'True':
        get_info_user(userid, filename)
    upload_status(filename)
    print("New Format is ready to be downloaded")
    sys.stdout.flush()
    return


def update_flag():
    cur = conn.cursor()
    cur.execute("UPDATE flag SET exceeded = true")
    conn.commit()
    cur.close()
    print("Flag updated")
    sys.stdout.flush()
    return


def get_info_user(userid, filename):
    cur = conn2.cursor()
    cur.execute('SELECT username, email FROM "user" WHERE id = %s', [userid])
    info = cur.fetchone()
    cur.close()
    send_email(filename, info[1], info[0])
    return info


def send_email(filename, email, username):
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
    if request.status_code == 200:
        print("Email sent!")
        sys.stdout.flush()
        return
    else:
        print("Something went wrong sending email")
        sys.stdout.flush()
        return


def upload_status(filename):
    cur = conn.cursor()
    cur.execute("UPDATE task SET status=(%s)"
                " WHERE filename = (%s)", ("processed", filename,))
    cur.execute("UPDATE task SET processed_at=(%s) WHERE filename = (%s)",
                (datetime.now(), filename))
    conn.commit()
    cur.close()
    print("Status updated")
    sys.stdout.flush()
    return


future = subscriber.subscribe(subscription_path, callback=callback)

while True:
    with subscriber:
        try:
            future.result()
        except Exception as e:
            print(f"Error on processing file: {e}")
            sys.stdout.flush()
