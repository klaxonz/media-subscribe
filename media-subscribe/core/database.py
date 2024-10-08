import contextlib
import datetime
import logging

from sqlalchemy import create_engine, Column, DateTime, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from core.config import settings

logger = logging.getLogger(__name__)

db_config = {
    'host': settings.MYSQL_HOST,
    'port': settings.MYSQL_PORT,
    'user': settings.MYSQL_USER,
    'password': settings.MYSQL_PASSWORD,
    'database': settings.MYSQL_DATABASE,
}

engine = create_engine(
    settings.database_url,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.POOL_MAX_SIZE,
    pool_recycle=settings.POOL_RECYCLE,
    connect_args={"init_command": "SET time_zone='+08:00'"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BaseMixin:
    """model的基类,所有model都必须继承"""
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now,
                        index=True)


class ModelBase(Base, BaseMixin):
    __abstract__ = True

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        super().__init__()


@event.listens_for(engine, "before_cursor_execute")
def comment_sql_calls(conn, cursor, statement, parameters, context, executemany):
    raw_sql = statement % parameters
    logger.debug(f"执行SQL: {raw_sql}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextlib.contextmanager
def get_session() -> Session:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception as e:
        s.rollback()
        raise e
    finally:
        s.close()


def get_db_session():
    return SessionLocal()
