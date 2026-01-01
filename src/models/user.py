from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
from configs.pgdb import BaseModel
from models.group import Group

class User(BaseModel):
    user_id = CharField(max_length=30, primary_key=True)
    nickname = CharField(max_length=100)


    class Meta:
        table_name = "user"
        indexes = (
            (('nickname',),False),
        )

    def __str__(self):
        return f"{self.nickname} ({self.user_id})"