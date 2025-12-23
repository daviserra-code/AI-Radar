from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models, crud, auth
from app.dependencies import templates, get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_current_admin_user)]
)

@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    users = crud.get_all_users(db)
    return templates.TemplateResponse(
        "admin_users.html", 
        {"request": request, "users": users, "current_user": current_user}
    )

@router.post("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = crud.toggle_user_active(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user)
):
    # Prevent self-demotion to avoid locking oneself out
    if user_id == current_user.id:
        # Flash message capability would be nice here, but for now just redirect
        return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
        
    user = crud.toggle_user_admin(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)

@router.post("/users/{user_id}/toggle-subscription")
async def toggle_subscription(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = crud.toggle_user_subscription(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_302_FOUND)
