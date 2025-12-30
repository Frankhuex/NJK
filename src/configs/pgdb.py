from peewee import PostgresqlDatabase
from peewee import Model
import os
from dotenv import load_dotenv

load_dotenv()


DB_CONFIG = {
    "database": os.getenv("DB_NAME") or "njk",
    "host": os.getenv("DB_HOST") or "localhost",
    "user": os.getenv("DB_USER") or "njk",
    "password": os.getenv("DB_PWD") or "1234",
    "port": os.getenv("DB_PORT") or 5432
}

pgdb: PostgresqlDatabase = PostgresqlDatabase(**DB_CONFIG)
print(pgdb)

class BaseModel(Model):
    class Meta:
        database = pgdb  # 关联数据库连接
        legacy_table_names = False  # 禁用旧表名规则（可选，避免类名自动转小写+复数）


print("Connected to PostgreSQL database: ",pgdb)