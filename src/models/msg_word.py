from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.word import Word
from models.message import Message

class MsgWord(BaseModel):
    message = ForeignKeyField(Message, backref='msg_words', on_delete='CASCADE')
    word = ForeignKeyField(Word, backref='msg_words', on_delete='CASCADE')

    class Meta:
        table_name = "msg_word"