# app.py - 现代化 SQLAlchemy 2.0 ORM 版本（含登录 + 分类筛选 + 简介）
import os
import uvicorn
import asyncio
import secrets
from datetime import date, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text

from database import engine, get_db, Book, Reader, BorrowRecord, FineRecord, BookCategory
from recommend import get_recommendations

# ============ 模板引擎配置 ============
jinja2_env = Environment(loader=FileSystemLoader("templates"), auto_reload=True, cache_size=0)
templates = Jinja2Templates(env=jinja2_env)

# ============ 应用生命周期 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ SQLAlchemy 异步数据库引擎就绪")
    yield
    await engine.dispose()
    print("✅ 数据库引擎已断开释放")

app = FastAPI(title="图书借阅管理系统 (ORM版)", version="2.0", lifespan=lifespan)

# Session 中间件（用于登录状态管理）
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))

# 静态文件挂载
app.mount("/static", StaticFiles(directory="static"), name="static")

executor = ThreadPoolExecutor(max_workers=4)

# ============ 管理员账号配置 ============
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"

# ============ 数据验证模型 ============
class BorrowRequest(BaseModel):
    reader_id: int
    book_id: str

class ReturnRequest(BaseModel):
    reader_id: int
    book_id: str

class PayFineRequest(BaseModel):
    fine_id: int

# ============ 登录相关路由 ============

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/api/login")
async def admin_login(request: Request):
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session["user"] = {"username": username, "logged_in": True}
        return {"success": True, "message": "登录成功！正在跳转..."}
    else:
        return {"success": False, "message": "用户名或密码错误，请重试！"}

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# ============ 主页面路由 ============
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = request.session.get("user")
    if not user or not user.get("logged_in"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="index.html")

# ============ ORM API 接口 ============

# 1. 搜索图书（支持关键词 + 分类筛选）
@app.get("/api/books/search")
async def search_books(
    keyword: Optional[str] = Query(None),
    category: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Book)
    if keyword:
        stmt = stmt.where(or_(Book.书名.like(f"%{keyword}%"), Book.作者.like(f"%{keyword}%")))
    if category and category > 0:
        stmt = stmt.where(Book.类别编号 == category)
    stmt = stmt.limit(50)
    
    result = await db.execute(stmt)
    books = result.scalars().all()
    
    return [
        {
            "图书编号": b.图书编号,
            "书名": b.书名,
            "作者": b.作者 or "佚名",
            "出版社": b.出版社,
            "简介": b.简介 or "暂无简介",
            "总库存": b.总库存,
            "现有库存": b.现有库存
        }
        for b in books
    ]

# 2. 获取所有可借图书
@app.get("/api/books/all")
async def get_all_books(db: AsyncSession = Depends(get_db)):
    stmt = select(Book).where(Book.现有库存 > 0)
    result = await db.execute(stmt)
    books = result.scalars().all()
    return [{"图书编号": b.图书编号, "书名": b.书名, "现有库存": b.现有库存} for b in books]

# 4. 借书业务
@app.post("/api/borrow")
async def borrow_book(req: BorrowRequest, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, req.book_id)
    if not book or book.现有库存 <= 0:
        return {"success": False, "message": "借阅失败：该图书暂无在馆库存！"}
    reader = await db.get(Reader, req.reader_id)
    if not reader or reader.已借数量 >= reader.最大借阅量:
        return {"success": False, "message": "借阅失败：读者借阅数量已达上限！"}
    try:
        new_record = BorrowRecord(
            读者编号=req.reader_id,
            图书编号=req.book_id,
            借出日期=date.today(),
            应还日期=date.today() + timedelta(days=30)
        )
        db.add(new_record)
        book.现有库存 -= 1
        reader.已借数量 += 1
        await db.commit()
        return {"success": True, "message": "借书成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"事务处理异常: {str(e)}")

# 5. 获取未还记录
@app.get("/api/borrowings/active")
async def get_active_borrowings(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(BorrowRecord)
        .where(BorrowRecord.归还日期.is_(None))
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "读者编号": rec.读者编号,
            "姓名": rec.reader.姓名 if rec.reader else "未知读者",
            "图书编号": rec.图书编号,
            "书名": rec.book.书名 if rec.book else "未知图书"
        }
        for rec in records
    ]

# 6. 还书业务
@app.post("/api/return")
async def return_book(req: ReturnRequest, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(
            text("CALL proc_办理还书业务(:reader_id, :book_id)"),
            {"reader_id": req.reader_id, "book_id": req.book_id}
        )
        await db.commit()
        return {"success": True, "message": "办理还书成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"业务处理失败: {str(e)}")

# 7. 获取未缴罚单
@app.get("/api/fines/unpaid")
async def get_unpaid_fines(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(FineRecord)
        .where(or_(FineRecord.备注 != "已缴费", FineRecord.备注.is_(None)))
    )
    result = await db.execute(stmt)
    fines = result.scalars().all()
    return [
        {
            "罚款编号": f.罚款编号,
            "姓名": f.borrowing.reader.姓名 if f.borrowing and f.borrowing.reader else "未知读者",
            "罚款金额": float(f.罚款金额),
            "罚款原因": f.罚款原因 or "逾期违约",
            "备注": f.备注 or "未缴费"
        }
        for f in fines
    ]

# 8. 缴纳罚金
@app.post("/api/pay_fine")
async def pay_fine(req: PayFineRequest, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("CALL proc_缴纳罚金(:fine_id)"), {"fine_id": req.fine_id})
        await db.commit()
        return {"success": True, "message": "缴费成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"缴费异常: {str(e)}")

# 9. 扫描逾期
@app.post("/api/scan_overdue")
async def scan_overdue(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("CALL proc_游标_扫描逾期记录()"))
        await db.commit()
        return {"success": True, "message": "逾期扫描完成！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# 10. 冻结违规账号
@app.post("/api/freeze_violators")
async def freeze_violators(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("CALL proc_游标_批量冻结违规账号()"))
        await db.commit()
        return {"success": True, "message": "违规账号已冻结！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# 11. 老赖名单
@app.get("/api/violators")
async def get_violators(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Reader)
        .where(Reader.账号状态 == "冻结")
    )
    result = await db.execute(stmt)
    violators = result.scalars().all()
    return [{"姓名": v.姓名, "联系电话": v.联系电话, "账号状态": v.账号状态} for v in violators]

# 12. AI 推荐
@app.get("/api/recommend/{reader_id}")
async def recommend_books(reader_id: int):
    loop = asyncio.get_event_loop()
    recs = await loop.run_in_executor(executor, get_recommendations, reader_id)
    return recs

# 13. 获取所有图书分类
@app.get("/api/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(BookCategory)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return [
        {
            "类别编号": c.类别编号,
            "类别名称": c.类别名称
        }
        for c in categories
    ]

# ============ 读者信息管理 API ============

# 14. 创建新读者
@app.post("/api/readers")
async def create_reader(request: Request, db: AsyncSession = Depends(get_db)):
    """创建新读者"""
    import re
    data = await request.json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()

    if not name:
        return {"success": False, "message": "姓名不能为空！"}
    if not phone:
        return {"success": False, "message": "联系电话不能为空！"}
    if not re.match(r'^1\d{10}$', phone):
        return {"success": False, "message": "请输入有效的11位手机号！"}

    try:
        stmt = select(Reader).where(Reader.联系电话 == phone)
        result = await db.execute(stmt)
        existing_reader = result.scalar_one_or_none()
        if existing_reader:
            return {"success": False, "message": f"该手机号已被注册（{existing_reader.姓名}），请勿重复添加！"}

        new_reader = Reader(
            姓名=name,
            联系电话=phone,
            已借数量=0,
            最大借阅量=5,
            账号状态="正常"
        )
        db.add(new_reader)
        await db.commit()
        await db.refresh(new_reader)

        return {
            "success": True,
            "message": f"✅ 读者 {name} 登记成功！",
            "reader": {
                "读者编号": new_reader.读者编号,
                "姓名": new_reader.姓名,
                "联系电话": new_reader.联系电话,
                "账号状态": new_reader.账号状态
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建读者失败: {str(e)}")


# 15. 获取所有读者信息
@app.get("/api/readers/all")
async def get_all_readers(db: AsyncSession = Depends(get_db)):
    """获取所有读者信息"""
    stmt = select(Reader).order_by(Reader.读者编号)
    result = await db.execute(stmt)
    readers = result.scalars().all()
    return [
        {
            "读者编号": r.读者编号,
            "姓名": r.姓名,
            "联系电话": r.联系电话 or "未设置",  # ✅ 加上这一行
            "已借数量": r.已借数量,
            "最大借阅量": r.最大借阅量,
            "账号状态": r.账号状态  # ✅ 加上这一行
        }
        for r in readers
    ]


# 16. 修改读者手机号
@app.put("/api/readers/{reader_id}/phone")
async def update_reader_phone(reader_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """修改读者手机号"""
    import re
    data = await request.json()
    new_phone = data.get("phone", "").strip()

    if not new_phone:
        return {"success": False, "message": "手机号不能为空！"}
    if not re.match(r'^1\d{10}$', new_phone):
        return {"success": False, "message": "请输入有效的11位手机号！"}

    stmt = select(Reader).where(Reader.联系电话 == new_phone, Reader.读者编号 != reader_id)
    result = await db.execute(stmt)
    existing_reader = result.scalar_one_or_none()
    if existing_reader:
        return {"success": False, "message": f"该手机号已被其他读者（{existing_reader.姓名}）使用！"}

    reader = await db.get(Reader, reader_id)
    if not reader:
        return {"success": False, "message": "读者不存在！"}

    old_phone = reader.联系电话
    reader.联系电话 = new_phone
    await db.commit()

    return {
        "success": True,
        "message": f"✅ 手机号修改成功！{old_phone} → {new_phone}",
        "new_phone": new_phone
    }


# 17. 注销读者
@app.delete("/api/readers/{reader_id}")
async def delete_reader(reader_id: int, db: AsyncSession = Depends(get_db)):
    """注销读者"""
    reader = await db.get(Reader, reader_id)
    if not reader:
        return {"success": False, "message": "读者不存在！"}

    stmt = select(BorrowRecord).where(
        BorrowRecord.读者编号 == reader_id,
        BorrowRecord.归还日期.is_(None)
    )
    result = await db.execute(stmt)
    active_borrowings = result.scalars().all()

    if active_borrowings:
        return {
            "success": False,
            "message": f"该读者仍有 {len(active_borrowings)} 本图书未归还，请先办理还书手续！"
        }

    reader_name = reader.姓名
    await db.delete(reader)
    await db.commit()

    return {"success": True, "message": f"✅ 读者 {reader_name} 已成功注销！"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)