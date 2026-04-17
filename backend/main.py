from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.imports import router as imports_router
from routes.transactions import router as transactions_router
from routes.insights import router as insights_router
from db.database import engine, Base
from db import models


app = FastAPI() # creates the app

# since frontend and backend run on different ports (origins), CORS middleware is needed to allow the frontend to make requests to the backend
# CORS = cross origin resource sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine) # create all the tables in the database (we do this here because we want to create the tables before the app starts)

@app.get("/")
def read_root():
    return {"message": "Backend is running"}

app.include_router(imports_router)
app.include_router(transactions_router)
app.include_router(insights_router)