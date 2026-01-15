from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- LOGIN ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if not user or user.password != password:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Hatalı kullanıcı adı veya şifre"})

    if not user.is_approved:
         return templates.TemplateResponse("login.html", {"request": request, "error": "Hesabınız henüz onaylanmadı. Lütfen yönetici onayını bekleyin."})
    
    # Super Admin Redirect
    if user.role == 'super_admin':
        response = RedirectResponse(url="/super-admin", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="user_session", value=user.username)
        return response

    # Normal Teacher Redirect
    response = RedirectResponse(url="/host", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_session", value=user.username)
    return response

# --- REGISTER ---
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...), 
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Bu kullanıcı adı zaten alınmış."})
    
    # Create Pending User
    new_user = models.User(
        username=username, 
        password=password, 
        role="teacher", 
        is_approved=False,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone
    )
    db.add(new_user)
    db.commit()
    
    return templates.TemplateResponse("register.html", {"request": request, "success": "Kayıt başarılı! Yönetici onayı bekleniyor."})

# --- LOGOUT ---
@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user_session")
    return response

# --- SUPER ADMIN ---
@router.get("/super-admin", response_class=HTMLResponse)
async def super_admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    # Verify Super Admin
    user = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not user or user.role != 'super_admin':
        return RedirectResponse("/host")
    
    # Fetch Pending Users
    pending_users = db.query(models.User).filter(models.User.is_approved == False).all()
    
    # Fetch Approved Users (Active Teachers)
    approved_users = db.query(models.User).filter(models.User.is_approved == True, models.User.role != 'super_admin').all()
    
    # Statistics
    stats = {
        "total_users": db.query(models.User).count(),
        "total_quizzes": db.query(models.Quiz).count(),
        "active_teachers": len(approved_users),
        "pending_approval": len(pending_users)
    }
    
    return templates.TemplateResponse("super_admin.html", {
        "request": request, 
        "pending_users": pending_users, 
        "approved_users": approved_users,
        "stats": stats,
        "admin_name": user.username
    })

@router.post("/super-admin/approve/{user_id}")
async def approve_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    admin = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not admin or admin.role != 'super_admin':
        return RedirectResponse("/host")
        
    user_to_approve = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_approve:
        user_to_approve.is_approved = True
        db.commit()
        
    return RedirectResponse(url="/super-admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/super-admin/reject/{user_id}")
async def reject_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    admin = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not admin or admin.role != 'super_admin':
        return RedirectResponse("/host")
        
    user_to_delete = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_delete:
         db.delete(user_to_delete)
         db.commit()
        
    return RedirectResponse(url="/super-admin", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/super-admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/super-admin/edit/{user_id}")
async def edit_user(
    user_id: int, 
    request: Request, 
    first_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    db: Session = Depends(get_db)
):
    user_cookie = request.cookies.get("user_session")
    if not user_cookie: return RedirectResponse("/login")
    
    admin = db.query(models.User).filter(models.User.username == user_cookie).first()
    if not admin or admin.role != 'super_admin':
        return RedirectResponse("/host")
        
    user_to_edit = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_edit:
        if first_name: user_to_edit.first_name = first_name
        if last_name: user_to_edit.last_name = last_name
        if email: user_to_edit.email = email
        if phone: user_to_edit.phone = phone
        db.commit()
    
    return RedirectResponse(url="/super-admin", status_code=status.HTTP_303_SEE_OTHER)

# --- PASSWORD RECOVERY ---
from itsdangerous import URLSafeTimedSerializer

# Secret key for token generation (In prod, move to Env Var)
SECRET_KEY = "bisual_secret_key_change_me"
security = URLSafeTimedSerializer(SECRET_KEY)

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})

@router.post("/forgot-password")
async def forgot_password_submit(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        # Security: Don't reveal if user exists. Delay slightly if needed to prevent timing attacks.
        return templates.TemplateResponse("forgot_password.html", {
            "request": request, 
            "message": "Eğer e-posta sistemde kayıtlıysa sıfırlama bağlantısı gönderildi."
        })
    
    # Generate Token (Valid for 1 hour)
    token = security.dumps(user.email, salt="password-reset-salt")
    
    # Generate Link
    # For now, we assume current host. In prod, use explicit domain.
    base_url = str(request.base_url).rstrip("/")
    reset_link = f"{base_url}/reset-password/{token}"
    
    # TODO: Send Email via SMTP
    # For now: Print to console
    print(f"\n[PASSWORD RESET] Link for {email}: {reset_link}\n")
    
    return templates.TemplateResponse("forgot_password.html", {
        "request": request, 
        "message": "Eğer e-posta sistemde kayıtlıysa sıfırlama bağlantısı gönderildi. (Geliştirici Notu: Link Terminalde)"
    })

@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str):
    try:
        email = security.loads(token, salt="password-reset-salt", max_age=3600)
    except:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Bağlantı geçersiz veya süresi dolmuş."})
        
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@router.post("/reset-password/{token}")
async def reset_password_submit(
    request: Request, 
    token: str,
    password: str = Form(...), 
    confirm_password: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        email = security.loads(token, salt="password-reset-salt", max_age=3600)
    except:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Bağlantı geçersiz veya süresi dolmuş."})
    
    if password != confirm_password:
        return templates.TemplateResponse("reset_password.html", {
            "request": request, 
            "token": token, 
            "error": "Şifreler eşleşmiyor."
        })
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Kullanıcı bulunamadı."})
    
    # Update Password
    user.password = password # In prod, ensure this is hashed! (Currently storing raw based on existing code)
    db.commit()
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz." # Using 'error' div for success message mostly to reuse style, or update login.html to support success msg
    })
