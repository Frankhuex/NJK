from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
from models.user import User
from models.group import Group
from models.topic import Topic
from configs.pgdb import BaseModel
from playhouse.postgres_ext import JSONField

class Message(BaseModel):
    message_id = CharField(max_length=30, primary_key=True)
    time = DateTimeField()
    sender = ForeignKeyField(User, field='user_id', backref='messages', null=True, on_delete='SET NULL')
    group = ForeignKeyField(Group, field='group_id', backref='messages', null=True, on_delete='SET NULL')
    card = CharField(max_length=100, null=True)
    text = CharField(null=True)
    reply = ForeignKeyField('self', column_name='reply_id', field='message_id', backref='replies', null=True, on_delete='SET NULL')
    raw_json = JSONField(null=True)

    class Meta:
        table_name = "message"

    def __str__(self):
        username: str = str(self.card if self.card else (self.sender.nickname if self.sender else "Unknown User"))
        return f"[{self.time}] {username}: {self.text}"
