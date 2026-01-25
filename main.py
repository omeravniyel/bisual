from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.routers import quiz, game, auth
from app import models
import shutil
import uuid
import sys
import os

app = FastAPI(title="BiSual - Interactive Quiz Platform")

# Helper for PyInstaller path
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Exception Handler for Debugging Production 500s
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    import traceback
    error_details = traceback.format_exc()
    print(f"CRITICAL ERROR: {error_details}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc), "trace": error_details.split('\n')},
    )

# Create DB tables
models.Base.metadata.create_all(bind=engine)

from sqlalchemy import inspect

# Auto-Migrate (Support both SQLite and Postgres)
def run_migrations():
    try:
        inspector = inspect(engine)
        if inspector.has_table("quizzes"):
            columns = [col['name'] for col in inspector.get_columns("quizzes")]
            
            # If table exists but settings column is missing
            if 'settings' not in columns:
                print("Migrating DB: Adding settings column...")
                with engine.begin() as conn:
                    # Generic SQL that works for both (Postgres supports JSON, SQLite supports it as affinity)
                    conn.execute(text("ALTER TABLE quizzes ADD COLUMN settings JSON DEFAULT '{}'"))
                print("Migration successful.")
    except Exception as e:
        print(f"Migration Init Warning: {e}")
        import traceback
        traceback.print_exc()

run_migrations()

# Version Check Route
@app.get("/version")
def get_version():
    return {"version": "1.0.0"}

# Manual Fix Route
@app.get("/fix-db")
def manual_fix_db():
    try:
        run_migrations()
        return {"status": "executed", "message": "Migration logic ran. Check logs or functionality."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Mount bundled static files (CSS, JS, Audio) - Read Only
app.mount("/static", StaticFiles(directory=resource_path("app/static")), name="static")

# Mount Uploads directory - Writable (Next to EXE or /tmp for Vercel)
# We ensure the folder exists
if os.environ.get("VERCEL"):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth.router, tags=["auth"])
app.include_router(quiz.router, prefix="/api", tags=["quiz"])
app.include_router(quiz.router, tags=["quiz_ui"])
app.include_router(game.router, tags=["game"])

# Initialize Admin User on Startup (Simplified)
@app.on_event("startup")
def create_initial_user():
    db = SessionLocal()
    if not db.query(models.User).filter(models.User.username == "admin").first():
        admin = models.User(username="admin", password="password", role="super_admin", is_approved=True)
        db.add(admin)
        db.commit()
    db.close()

# Templates
templates = Jinja2Templates(directory=resource_path("app/templates"))

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # Create valid filename
    file_ext = file.filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{file_ext}"
    
    # Save to external 'uploads' folder (writable path)
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/static/uploads/{filename}"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "BiSual Home"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
