import os
import time
from datetime import datetime
import datetime as dt
from dotenv import load_dotenv
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask import Flask, request, send_file
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import json
from celery import Celery

load_dotenv()

app = Flask(__name__)
redis_host = os.environ['REDIS_HOST']
redis_uri = "redis://{}:6379/0".format(redis_host)
simple = Celery('simple_worker', broker=redis_uri,
                backend=redis_uri)

db_uri = "postgresql://{}:{}@{}:5432/tasks".format(os.environ['DB_USER'], os.environ['DB_PASSWORD'], os.environ['DB_HOST'])

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config["JWT_SECRET_KEY"] = os.environ['JWT_SECRET']

db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
api = Api(app)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(100))
    new_format = db.Column(db.String(10))
    status = db.Column(db.String(15))
    timestamp = db.Column(db.DateTime(timezone=False))
    user_id = db.Column(db.Integer)
    processed_at = db.Column(db.DateTime(timezone=False))


class Flag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    exceeded = db.Column(db.Boolean)


class TaskSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ("id", "filename", "new_format",
                  "status", "timestamp", "user_id", "processed_at")


class FlagSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ("id", "exceeded")


task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)
flag_schema = FlagSchema()

with app.app_context():
    db.create_all()
    if (len(Flag.query.all()) == 0):
        task = Flag(exceeded=False)
        db.session.add(task)
        db.session.commit()


class TasksResource(Resource):
    @jwt_required()
    def post(self):
        flag = Flag.query.first()
        if (flag.exceeded):
            return "A file start processing time has exceeded 10 minutes", 400
        new_format = request.form['newFormat']
        file = request.files['fileName']
        user_id = get_jwt_identity()
        start = time.time()
        timestr = dt.datetime.fromtimestamp(start).strftime('%Y%m%d-%H%M%S')
        filename = file.filename.split(".")[0]
        format = file.filename.split(".")[1]
        filename = "{}_{}.{}".format(filename, timestr, format)
        file.save("./files/{}".format(filename))

        new_task = Task(
            filename=filename,
            new_format=new_format,
            status="uploaded",
            timestamp=datetime.strptime(datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S'),
            user_id=user_id)

        db.session.add(new_task)
        db.session.commit()
        app.logger.info("Invoking task audio_converter")
        r = simple.send_task('tasks.audio_converter', kwargs={'filename': filename,
                                                              'new_format': new_format,
                                                              'userid': user_id,
                                                              'timestamp': start
                                                              })
        app.logger.info(r.backend)

        return {"message": "Tarea creada exitosamente"}, 200

    @jwt_required()
    def get(self):
        order = None
        limit = None
        args = request.args
        try:
            order = int(args.get('order'))
            limit = int(args.get('limit'))
        except ValueError:
            return "Invalid parameters", 400

        if (order == 1):
            user_id = get_jwt_identity()
            task = Task.query.filter(Task.user_id == user_id).order_by(
                Task.id.desc()).limit(limit).all()
        elif (order == 0):
            user_id = get_jwt_identity()
            task = Task.query.filter(Task.user_id == user_id).order_by(
                Task.id.asc()).limit(limit).all()
        else:
            return "Nothing to do", 400

        if task is None:
            return "Task not found", 404

        return tasks_schema.dump(task, many=True), 200


class TaskResource(Resource):
    @jwt_required()
    def put(self, task_id):
        new_format = request.json['newFormat']
        user_id = get_jwt_identity()
        task = Task.query.filter(
            Task.id == task_id, Task.user_id == user_id).first()

        if task is None:
            return "Task not found", 404
        if task.new_format == new_format:
            return "Nothing to do", 400

        if task.status == "uploaded":
            task.new_format = new_format
            db.session.commit()
        if task.status == "processed":
            os.remove(
                "./files/{}.{}".format(task.filename.split(".")[0], task.new_format))

            task.new_format = new_format
            task.status = "uploaded"
            db.session.commit()
            r = simple.send_task('tasks.audio_converter', kwargs={'filename': task.filename,
                                                              'new_format': new_format,
                                                              'userid': user_id,
                                                              'timestamp': time.time()
                                                              })
            app.logger.info(r.backend)

        return task_schema.dump({
            "id": task.id,
            "filename": task.filename,
            "new_format": task.new_format,
            "status": task.status,
            "timestamp": task.timestamp,
            "user_id": task.user_id
        }), 200

    @jwt_required()
    def delete(self, task_id):
        user_id = get_jwt_identity()
        task = Task.query.filter(
            Task.id == task_id, Task.user_id == user_id).first()

        if task is None:
            return "Task not found", 404

        os.remove("./files/{}".format(task.filename))

        if task.status == "processed":
            os.remove("./files/{}.{}".format(task.filename.split('.')[0], task.new_format))

        Task.query.filter(Task.id == task_id, Task.user_id == user_id).delete()
        db.session.commit()
        return

    @jwt_required()
    def get(self, task_id):
        user_id = get_jwt_identity()
        task = Task.query.filter(
            Task.id == task_id, Task.user_id == user_id).first()

        if task is None:
            return "Task not found", 404

        return task_schema.dump({
            "id": task.id,
            "filename": task.filename,
            "new_format": task.new_format,
            "status": task.status,
            "timestamp": task.timestamp,
            "user_id": task.user_id
        }), 200


class FileResource(Resource):
    @jwt_required()
    def get(self, filename):
        return send_file("./files/{}".format(filename), download_name=filename)

class HealthResource(Resource):
    def get(self):
        return "ok", 200
    
api.add_resource(TasksResource, '/api/tasks')
api.add_resource(TaskResource, '/api/tasks/<int:task_id>')
api.add_resource(FileResource, '/api/files/<string:filename>')
api.add_resource(HealthResource, '/api/health')


def return_app():
    return app

