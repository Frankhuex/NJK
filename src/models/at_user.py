from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.user import User
from models.message import Message

class AtUser(BaseModel):
    message = ForeignKeyField(Message, backref='at_users', on_delete='CASCADE')
    user = ForeignKeyField(User, backref='at_users', on_delete='CASCADE')

    class Meta:
        table_name = "at_user"