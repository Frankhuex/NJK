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

from playhouse.migrate import PostgresqlMigrator, migrate

migrator = PostgresqlMigrator(pgdb)
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

def index_exists(db, table_name, fields, unique=False):
    """
检查数据库中是否已存在指定的索引
    fields: 字段元组，如 ('group',) 或 ('group', 'name')
    """
    # 生成索引名（与peewee命名规则一致）
    fields_str = '_'.join(fields)
    index_name = f"idx_{table_name}_{fields_str}"
    if unique:
        index_name = f"{index_name}_unique"

    try:
        result = db.execute_sql("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = %s AND indexname = %s
        """, (table_name, index_name))
        return result.fetchone() is not None
    except:
        return False

if __name__ == '__main__':
    print("开始添加索引...\n")

    for Model in models:
        if hasattr(Model._meta, 'indexes') and Model._meta.indexes:
            print(f"🔍 {Model._meta.table_name} 索引:")
            for fields, unique in Model._meta.indexes:
                try:
                    migrate(
                        migrator.add_index(Model._meta.table_name, fields, unique=unique)
                    )
                    print(f"✅ {Model._meta.table_name}.{fields}")
                except Exception as e:
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        print(f"⚠️  跳过: {Model._meta.table_name}.{fields} (已存在)")
                    else:
                        print(f"❌ 错误: {Model._meta.table_name}.{fields} - {e}")

    print("\n完成！")