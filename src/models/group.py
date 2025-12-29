from peewee import CharField, IntegerField, BooleanField, DateTimeField
from configs.pgdb import BaseModel

class Group(BaseModel):
    group_id = CharField(max_length=30, primary_key=True)
    group_name = CharField(max_length=100)

    class Meta:
        table_name = "group"