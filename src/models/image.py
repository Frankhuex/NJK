from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.user import User
from models.message import Message

class Image(BaseModel):
    id = AutoField(primary_key=True)
    message = ForeignKeyField(Message, backref='images', on_delete='CASCADE')
    image_hash = CharField(max_length=100)

    class Meta:
        table_name = "image"
        indexes = (
            (("message_id",), False),
            (("image_hash",), False),
        )