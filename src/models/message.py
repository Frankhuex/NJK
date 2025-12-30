from peewee import CharField, IntegerField, BooleanField, DateTimeField, ForeignKeyField
from models.user import User
from models.group import Group
from models.topic import Topic
from configs.pgdb import BaseModel
from playhouse.postgres_ext import JSONField
import json

class Message(BaseModel):
    message_id = CharField(max_length=30, primary_key=True)
    time = DateTimeField()
    sender = ForeignKeyField(User, field='user_id', backref='messages', null=True, on_delete='SET NULL')
    group = ForeignKeyField(Group, field='group_id', backref='messages', null=True, on_delete='SET NULL')
    card = CharField(max_length=100, null=True)
    text = CharField(null=True)
    reply = ForeignKeyField('self', column_name='reply_id', field='message_id', backref='replies', null=True, on_delete='SET NULL')
    raw_json = JSONField(null=True)
    raw_message = CharField(null=True)

    class Meta:
        table_name = "message"
        indexes = (
            # 基础索引
            (('time',), False),  # ✅ 必须加：最常用的查询字段
            
            # 外键索引
            (('group_id',), False),  # ✅ 按群组查询
            (('sender_id',), False),  # ✅ 按发送者查询
            (('reply_id',), False),  # ✅ 条件索引，回复查询
            
            # 复合索引（覆盖常用查询场景）
            (('group_id', 'time'), False),  # ✅ 查看群组历史
            (('sender_id', 'time'), False),  # ✅ 查看用户发言记录
            
            # 特定场景索引
            (('group_id', 'sender_id', 'time'), False),  # ✅ 群组内特定用户发言
        )

    def __str__(self):
        username: str = str(self.card if self.card else (self.sender.nickname if self.sender else "Unknown User"))
        user_id: str = str(self.sender.user_id if self.sender else "")
        return f"[{self.time}] {username} ({user_id}): {self.text}"
        # return str({
        #     "群友": username,
        #     "群友id": user_id,
        #     "发言": self.text,
        #     "消息id": self.message_id,
        #     "时间": str(self.time),
        # })
