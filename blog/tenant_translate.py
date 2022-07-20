from contextlib import contextmanager
import os
from pathlib import Path
from typing import Optional
from fastapi import Depends, Request
from sqlalchemy import engine_from_config
from alembic.config import Config
from blog import models
from blog.database import SessionLocal

BASE_DIR = Path(__file__).resolve().parent.parent
config = Config(os.path.join(BASE_DIR, 'alembic.ini'))

def get_tenant(req: Request) -> models.Tenant:
    host_without_port = req.headers["host"].split(":", 1)[0].split('.')[0]

    with with_db(None) as db:
      tenant = db.query(models.Tenant).filter(models.Tenant.host==host_without_port).one_or_none()

    if tenant is None:
        raise Exception("Tenant not found")

    return tenant

def get_db(tenant: models.Tenant = Depends(get_tenant)):
    with with_db(tenant.schema) as db:
        yield db

@contextmanager
def with_db(tenant_schema: Optional[str]):
    if tenant_schema:
        schema_translate_map = dict(tenant=tenant_schema)
    else:
        schema_translate_map = None

    connectable = engine_from_config(config.get_section(config.config_ini_section)).execution_options(schema_translate_map=schema_translate_map)

    
    db = SessionLocal(autocommit=False, autoflush=False, bind=connectable)
    try:
        yield db
    finally:
        db.close()