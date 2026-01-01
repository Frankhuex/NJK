from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.topic import Topic
from models.message import Message

class MsgTopic(BaseModel):
    message = ForeignKeyField(Message, backref='msg_topics', on_delete='CASCADE')
    topic = ForeignKeyField(Topic, backref='msg_topics', on_delete='CASCADE')

    class Meta:
        table_name = "msg_topic"
        indexes = (
            (('message_id',),False),
            (('topic_id',),False),
            (('message_id', 'topic_id'),False),
        )