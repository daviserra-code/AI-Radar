from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models, auth, crud
from app.dependencies import templates, get_db

router = APIRouter(tags=["authentication"])

@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    subscribe: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        # Check if user exists
        if db.query(models.User).filter(models.User.email == email).first():
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Email already registered"},
            )
        
        is_sub = True if subscribe else False
        
        # Create user
        hashed_pw = models.User.hash_password(password)
        new_user = models.User(
            username=username,
            email=email,
            hashed_password=hashed_pw,
            is_subscribed=is_sub
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Auto-login
        access_token = auth.create_access_token(data={"sub": new_user.username})
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,  # 30 minutes
            samesite="lax",
            secure=False,  # Set True in production with HTTPS
        )
        return response

    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Registration failed: {str(e)}"},
        )

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.verify_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_get(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
):
    return templates.TemplateResponse(
        "profile.html", {"request": request, "current_user": current_user}
    )


@router.post("/profile/password", response_class=HTMLResponse)
async def profile_password_post(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # Verify current password
    if not current_user.verify_password(current_password):
        return templates.TemplateResponse(
            "profile.html", 
            {"request": request, "current_user": current_user, "error": "Password attuale non corretta"}
        )
    
    # Verify new passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "profile.html", 
            {"request": request, "current_user": current_user, "error": "Le nuove password non coincidono"}
        )
    
    # Update password
    # Note: We need to import the crud function for this. 
    # Since crud was not imported fully as `from . import crud`, but `from app import models, auth, crud` in main, 
    # let's check imports in this file. Line 6 says `from app import models, auth`. 
    # We need crud.
    
    success = crud.update_user_password(db, current_user.id, new_password)
    
    if success:
        return templates.TemplateResponse(
            "profile.html", 
            {"request": request, "current_user": current_user, "success": "Password aggiornata con successo!"}
        )
    else:
        return templates.TemplateResponse(
            "profile.html", 
            {"request": request, "current_user": current_user, "error": "Errore durante l'aggiornamento della password"}
        )
