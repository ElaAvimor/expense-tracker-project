import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///../backend-data/app.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)  # connect to the database

SessionLocal = sessionmaker(bind=engine, autoflush=False,autocommit=False)  # create a session to interact with the db

Base = declarative_base()  # create a base class for the models
