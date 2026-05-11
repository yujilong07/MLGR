from sqlmodel import create_engine, Session, SQLModel
from app.config import settings

DATABASE_URL = settings.database_url
# default
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session