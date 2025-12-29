from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.group import Group

class Word(BaseModel):

    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True, null=False)
    group = ForeignKeyField(Group, field='group_id', backref='words', null=True, on_delete='SET NULL')


    class Meta:
        table_name = "word"