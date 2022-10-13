import os
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_TASKS_URI']
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


class TaskSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ("id", "filename", "new_format",
                  "status", "timestamp", "user_id")


task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)

with app.app_context():
    db.create_all()


class TasksResource(Resource):
    @jwt_required()
    def post(self):
        new_format = request.form['newFormat']
        file = request.files['fileName']
        user_id = get_jwt_identity()

        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = file.filename.split(".")[0]
        format = file.filename.split(".")[1]
        filename = "{}_{}.{}".format(filename, timestr, format)
        file.save(filename)

        new_task = Task(
            filename=filename,
            new_format=new_format,
            status="uploaded",
            timestamp=datetime.strptime(datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S'),
            user_id=user_id)

        db.session.add(new_task)
        db.session.commit()

        return {"message": "Tarea creada exitosamente"}, 200


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
            os.remove("./{}.{}".format(task.filename.split(".")[0],task.new_format))
            
            task.new_format = new_format
            task.status = "uploaded"
            db.session.commit()

        return task_schema.dump({
            "id": task.id,
            "filename": task.filename,
            "new_format": task.new_format,
            "status": task.status,
            "timestamp": task.timestamp,
            "user_id": task.user_id
        }), 200


api.add_resource(TasksResource, '/api/tasks')
api.add_resource(TaskResource, '/api/tasks/<int:task_id>')


def return_app():
    return app
