import os
from flask import Flask
from dotenv import load_dotenv
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

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


class TaskSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ("id", "filename", "new_format", "status", "timestamp")


task_schema = TaskSchema()

with app.app_context():
    db.create_all()


@app.route('/api/ms-tasks')
def hello():
    return 'Hello, World!'


def return_app():
    return app
