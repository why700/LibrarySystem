# routers/auth.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import ADMIN_USERNAME, ADMIN_PASSWORD

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """显示登录页面"""
    return templates.TemplateResponse(request=request, name="login.html")

@router.post("/api/login")
async def admin_login(request: Request):
    """处理登录请求"""
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["user"] = {"username": username, "logged_in": True}
        return {"success": True, "message": "登录成功！正在跳转..."}
    else:
        return {"success": False, "message": "用户名或密码错误，请重试！"}

@router.get("/logout")
async def logout(request: Request):
    """退出登录"""
    request.session.clear()
    return RedirectResponse(url="/login")