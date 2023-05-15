from sqlalchemy import event, ForeignKey, TEXT
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_async_engine("sqlite+aiosqlite:///db.sqlite")
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    type_annotation_map = {
        str: TEXT
    }


class Guild(Base):
    __tablename__ = 'guilds'

    id: Mapped[int] = mapped_column(primary_key=True)
    sentinel_channel_id: Mapped[int | None]

    minecraft_channel_id: Mapped[int | None]
    minecraft_rcon_address: Mapped[str | None]
    minecraft_rcon_pass: Mapped[str | None]

    wordle_channel_id: Mapped[int | None]

    members: Mapped[list['Member']] = relationship(
        back_populates='guild', cascade='save-update, merge, expunge, delete, delete-orphan'
    )


class Member(Base):
    __tablename__ = 'members'

    user_id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey('guilds.id'), primary_key=True)
    guild: Mapped['Guild'] = relationship(back_populates='members')

    minecraft_username: Mapped[str | None]
