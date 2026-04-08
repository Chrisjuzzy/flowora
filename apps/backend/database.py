from sqlalchemy import create_engine, Column, Integer, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr
from config import settings
from tenancy import get_current_tenant


class TenantMixin:
    @declared_attr
    def tenant_id(cls):
        return Column(
            Integer,
            ForeignKey("organizations.id"),
            index=True,
            nullable=True,
            default=get_current_tenant
        )

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.strip()
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = "postgresql://" + SQLALCHEMY_DATABASE_URL[len("postgres://"):]

engine_kwargs = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base(cls=TenantMixin)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
