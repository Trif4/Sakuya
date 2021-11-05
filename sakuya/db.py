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

    minecraft_channel_id = db.Column(db.Integer)
    minecraft_rcon_address = db.Column(db.Text)
    minecraft_rcon_pass = db.Column(db.Text)

    mewo_enabled = db.Column(db.Boolean)

    members = db.relationship('Member', backref='guild', cascade='all, delete-orphan')


class Member(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer, db.ForeignKey('guilds.id'), primary_key=True)
    minecraft_username = db.Column(db.Text)
    mewo_text = db.Column(db.Text)
