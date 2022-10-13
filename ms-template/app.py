import os
from flask import Flask
from dotenv import load_dotenv
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI']
app.config["JWT_SECRET_KEY"] = os.environ['JWT_SECRET']

db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
api = Api(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    password = db.Column(db.Integer)
    email = db.Column(db.String(100))


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        fields = ("id", "name", "email")


user_schema = UserSchema()

with app.app_context():
    db.create_all()


@app.route('/ms-template')
def hello():
    return 'Hello, World!'


def return_app():
    return app
