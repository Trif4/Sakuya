from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqla_wrapper import SQLAlchemy


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


db = SQLAlchemy('sqlite:///db.sqlite')


class Guild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sentinel_channel_id = db.Column(db.Integer)


db.create_all()
