import os
import re
import bcrypt
from dotenv import load_dotenv
from flask import Flask, request
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token
from flask_marshmallow import Marshmallow

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_USERS_URI']
app.config["JWT_SECRET_KEY"] = os.environ['JWT_SECRET']

db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
api = Api(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(255))
    email = db.Column(db.String(100), unique=True)


with app.app_context():
    db.create_all()


class SignUpResource(Resource):
    def post(self):
        password = request.json['password1']
        password_pattern = "^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9]).{8,}$"

        if password != request.json['password2']:
            return "Passwords do not match", 400
        if re.match(password_pattern, password) is None:
            return "Password must contain lowercase letters, uppercase letters and digits and at least 8 characters", 400

        new_user = User(
            username=request.json['username'],
            password=bcrypt.hashpw(
                password.encode('utf-8'), bcrypt.gensalt(10)).decode('utf-8'),
            email=request.json['email']
        )

        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(new_user)

        return {"message":"User created"}, 201

class SignInResource(Resource):
    def post(self):
        username = request.json['username']
        password = request.json['password'].encode('utf-8')
        
        user = User.query.filter(User.username==username).first()
        
        if user is None:
            return "Wrong credentials", 400
        
        if not bcrypt.checkpw(password, user.password.encode('utf-8')):
            return "Wrong credentials", 400
        
        return {"token": create_access_token(identity=user.id)}, 200

api.add_resource(SignUpResource, '/api/auth/signup')
api.add_resource(SignInResource, '/api/auth/signin')


def return_app():
    return app
