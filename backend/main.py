from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.dashboard import router as dashboard_router
from routes.handle_import import router as handle_import_router
from routes.insights import router as insights_router
from routes.list_imports import router as imports_router
from routes.transactions import router as transactions_router

from db.database import engine, Base


app = FastAPI() # creates the app

# since frontend and backend run on different ports (origins),
# CORS middleware is needed to allow the frontend to make requests to the backend
# CORS = cross-origin resource sharing
allow_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://expense-tracker-3dc4c.web.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create all the tables in the database (we do this here because we want to create the tables before the app starts)
Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


app.include_router(dashboard_router)
app.include_router(handle_import_router)
app.include_router(insights_router)
app.include_router(imports_router)
app.include_router(transactions_router)

