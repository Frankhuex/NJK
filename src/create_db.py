from configs.pgdb import pgdb
from models.user import User
from models.group import Group
from models.topic import Topic
from models.word import Word
from models.message import Message
from models.at_user import AtUser
from models.msg_topic import MsgTopic
from models.msg_word import MsgWord
from models.image import Image


models = [
    User,      # 被 Message 引用
    Group,     # 被 Topic, Word, Message 引用
    Topic,     # 被 Message, MsgTopic 引用
    Word,      # 被 MsgWord 引用
    Message,   # 自引用，被 AtUser, MsgTopic, MsgWord 引用
    AtUser,    # 多对多中间表
    MsgTopic,  # 多对多中间表
    MsgWord,   # 多对多中间表
    Image
]

pgdb.create_tables(models, safe=True)