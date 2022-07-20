from contextlib import contextmanager
import os
from pathlib import Path
from typing import Optional
import alembic
from fastapi import Depends, FastAPI, Request
from sqlalchemy import MetaData
import sqlalchemy
from blog.tenant_translate import with_db

from blog.routers import authentication
from . import models
from .database import Base, engine
from .routers import blog, user, authentication
from alembic.migration import MigrationContext
from alembic.config import Config
from sqlalchemy import schema
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
alembic_config = Config(os.path.join(BASE_DIR, 'alembic.ini'))

def get_shared_metadata():
    meta = MetaData()
    for table in Base.metadata.tables.values():
        if table.schema != "tenant":
            table.tometadata(meta)
    return meta

def get_tenant_specific_metadata():
    meta = MetaData(schema="tenant")
    for table in Base.metadata.tables.values():
        if table.schema == "tenant":
            table.tometadata(meta)
    return meta

def tenant_create(name: str, schema: str, host: str) -> None:
    with with_db(schema) as db:

        context = MigrationContext.configure(db.connection())
        script = alembic.script.ScriptDirectory.from_config(alembic_config)
        if context.get_current_revision() != script.get_current_head():
            raise RuntimeError(
                "Database is not up-to-date. Execute migrations before adding new tenants."
            )
        tenant = models.Tenant(
            name=name,
            host=host,
            schema=schema,
        )
        db.add(tenant)

        db.execute(sqlalchemy.schema.CreateSchema(schema))
        get_tenant_specific_metadata().create_all(bind=db.connection())

        db.commit()

with engine.begin() as db:
    context = MigrationContext.configure(db)
    if context.get_current_revision() is not None:
        print("Database already exists.")
    inspector = sqlalchemy.inspect(engine)
    shared_schema = 'shared'
    if shared_schema in inspector.get_schema_names():
        print(f"{shared_schema} schema exists")
    else:
        db.execute(schema.CreateSchema("shared"))
    get_shared_metadata().create_all(bind=db)

    alembic_config.attributes["connection"] = db
    # alembic.command.stamp(alembic_config, "head", purge=True)
# models.Base.metadata.create_all(engine)
# tenant_create(name='tenant_default', schema='tenant_default', host='tenant_default')

app.include_router(blog.router)
app.include_router(user.router)
app.include_router(authentication.router)

