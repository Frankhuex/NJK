from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.user import User
from models.message import Message

class ImgWhitelist(BaseModel):
    id = AutoField(primary_key=True)
    image_hash = CharField(max_length=100,unique=True)

    class Meta:
        table_name = "img_whitelist"