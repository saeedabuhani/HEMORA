import os
os.environ["DATABASE_URL"]="sqlite:///:memory:"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
from app.main import app
from app import models as m
from app.security import hash_password
from app.limiting import limiter

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,expire_on_commit=False)
@pytest.fixture
def db():
    Base.metadata.create_all(engine); session=TestingSession()
    yield session
    session.close(); Base.metadata.drop_all(engine)
@pytest.fixture
def client(db):
    def override(): yield db
    app.dependency_overrides[get_db]=override
    limiter.enabled=False  # login throttling is shared per-IP and would trip across tests
    yield TestClient(app)
    limiter.enabled=True
    app.dependency_overrides.clear()
@pytest.fixture
def users(db):
    admin=m.User(email="admin@test.local",password_hash=hash_password("Pass123!"),role=m.Role.ADMIN); patient=m.User(email="patient@test.local",password_hash=hash_password("Pass123!"),role=m.Role.PATIENT)
    db.add_all([admin,patient]); db.commit(); return admin,patient
