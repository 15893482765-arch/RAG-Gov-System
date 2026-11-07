from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker,Session
from app.config import get_settings
from collections.abc import Generator
class Base(DeclarativeBase):
    pass
settings=get_settings()
engine:Engine=create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True
)
SessionLocal=sessionmaker(
    bind=engine,
    expire_on_commit=False
)
def get_session()->Generator[Session,None,None]:
    with SessionLocal() as session:
        yield session
def init_database()->None:
    import app.models

    print("已注册的表：", Base.metadata.tables.keys())
    Base.metadata.create_all(engine)
    print("-----------------------")







