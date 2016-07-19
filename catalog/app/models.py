from app import db
from flask import url_for
import datetime
import json


class Category(db.Model):
    """Cateogry model"""

    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def serialize(self):
        return {'name': self.name}


class Item(db.Model):
    """Catalog item model"""

    __tablename__ = 'item'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    name = db.Column(db.String(250))
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category')
    image = db.Column(db.String(50))

    def __init__(self, user, name, description, category, image):
        self.user = user
        self.name = name
        self.description = description
        self.category = category
        self.image = image

    def serialize(self):
        return {
            'name': self.name,
            'owner': self.user.name,
            'category': self.category.name,
            'description': self.description,
            'image': url_for('static',
                             filename='img_store/' + self.image,
                             _external=True),
        }


class User(db.Model):
    """User model"""

    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))
    name = db.Column(db.String(200), nullable=True)
    pic = db.Column(db.String(2100))

    def __init__(self, user_id, name, pic):
        self.user_id = str(user_id)
        self.name = str(name)
        self.pic = str(pic)

    def serialize(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'pic': self.pic
        }
