from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField, AutoField
from configs.pgdb import BaseModel
from models.user import User
from models.message import Message

class AtUser(BaseModel):
    message = ForeignKeyField(Message, backref='at_users', on_delete='CASCADE')
    user = ForeignKeyField(User, backref='at_users', on_delete='CASCADE')

    class Meta:
        table_name = "at_user"
        indexes = (
            # ✅ 主索引：查询最常用的组合
            (('message_id', 'user_id'), True),  # 唯一索引，防止重复@
            
            # ✅ 反向查询索引
            (('user_id', 'message_id'), False),  # 按用户查被@的消息
            
            # ✅ 为 JOIN 优化
            (('message_id',), False),  # 单独 message 索引
            
            # ✅ 统计优化
            (('user_id',), False),  # 条件索引
        )