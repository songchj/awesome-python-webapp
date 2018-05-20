import time

from transwarp.db import next_id
from transwarp.orm import Model, StringField, BooleanField, FloatField, TextField

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(updatable=False, dll='varchar(50)')
    password = StringField(dll='varchar(50)')
    admin = BooleanField()
    name = StringField(dll='varchar(50)')
    image = StringField(dll='varchar(500)')
    created_at = FloatField(updatable=False, default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, dll='varchar(50)')
    user_id = StringField(updatable=False, dll='varchar(50)')
    user_name = StringField(dll='varchar(50)')
    user_image = StringField(dll='varchar(50)')
    name = StringField(dll='varchar(50)')
    summary = StringField(dll='varchar(200)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, dll='varchar(50)')
    blog_id = StringField(updatable=False, dll='varchar(50)')
    user_id = StringField(updatable=False, dll='varchar(50)')
    user_name = StringField(dll='varchar(50)')
    user_image = StringField(dll='varchar(500)')
    content = TextField()
    created_at = FloatField(updatable=False, default=time.time)