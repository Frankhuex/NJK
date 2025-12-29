from peewee import PostgresqlDatabase
from peewee import Model


DB_CONFIG = {
    "database": "njk2",
    "host": "localhost",
    "user": "postgres",
    "password": "114514",
    "port": 5432
}

pgdb: PostgresqlDatabase = PostgresqlDatabase(**DB_CONFIG)


class BaseModel(Model):
    class Meta:
        database = pgdb  # 关联数据库连接
        legacy_table_names = False  # 禁用旧表名规则（可选，避免类名自动转小写+复数）


print("Connected to PostgreSQL database: ",pgdb)