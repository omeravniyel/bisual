import PyInstaller.__main__
import os
import shutil

# Make sure we are in the right directory
if not os.path.exists("main.py"):
    print("Error: Please run this script from the project root directory (where main.py is).")
    exit(1)

# Clean previous builds
if os.path.exists("build"): shutil.rmtree("build")
if os.path.exists("dist"): shutil.rmtree("dist")

print("🚀 Starting Build Process for BiSual...")

PyInstaller.__main__.run([
    'main.py',
    '--name=BiSual',
    '--onefile',
    '--noconsole',  # Hide console window? Maybe keep it for debugging initially, let's keep it for now for server logs.
    # '--windowed', # Use this if we want to hide console, but uvicorn needs to run.
    
    # Add Data Files
    '--add-data=app/templates;app/templates',
    '--add-data=app/static;app/static', 
    # Note: We do NOT add uploads here, it's external.
    
    # Hidden Imports (FastAPI/Uvicorn/SQLAlchemy often need these)
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
    '--hidden-import=engineio.async_drivers.asciiv',
    '--hidden-import=engineio.async_drivers.threading',
    
    # Icon (Optional, if you had one)
    # '--icon=icon.ico',
])

print("\n✅ Build Complete!")
print("file is located at: dist/BiSual.exe")
print("⚠️ IMPORTANT: Copy 'dist/BiSual.exe' to a new folder.")
print("The 'uploads' folder and 'bisual.db' will be created next to it automatically on first run.")
