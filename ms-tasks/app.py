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


api.add_resource(TasksResource, '/api/tasks')


def return_app():
    return app
