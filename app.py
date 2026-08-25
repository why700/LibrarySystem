# app.py
import secrets
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware

from database import engine
from routers import auth, books, borrow, fines, readers, admin

# 模板配置
jinja2_env = Environment(loader=FileSystemLoader("templates"), auto_reload=True, cache_size=0)
templates = Jinja2Templates(env=jinja2_env)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ SQLAlchemy 异步数据库引擎就绪")
    yield
    await engine.dispose()
    print("✅ 数据库引擎已断开释放")

app = FastAPI(title="图书借阅管理系统 (模块化版)", version="2.0", lifespan=lifespan)

# 中间件与静态文件
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============ 挂载各个业务路由 ============
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(borrow.router)
app.include_router(fines.router)
app.include_router(readers.router)
app.include_router(admin.router)

# 首页路由拦截
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = request.session.get("user")
    if not user or not user.get("logged_in"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="index.html")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)