# app.py - 现代化 SQLAlchemy 2.0 ORM 完整版（业务逻辑全内置，不依赖 MySQL 触发器与存储过程）
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
from sqlalchemy import select, or_, and_, text, union
from sqlalchemy.orm import joinedload

from database import engine, get_db, Book, Reader, BorrowRecord, FineRecord, BookCategory
from recommend import get_recommendations
from templates.config import ADMIN_USERNAME, ADMIN_PASSWORD

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

app = FastAPI(title="图书借阅管理系统 (ORM全功能版)", version="2.0", lifespan=lifespan)

# Session 中间件
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))

# 静态文件挂载
app.mount("/static", StaticFiles(directory="static"), name="static")

executor = ThreadPoolExecutor(max_workers=4)

# ============ 数据验证模型 ============
class BorrowRequest(BaseModel):
    reader_id: int
    book_id: str

class ReturnRequest(BaseModel):
    reader_id: int
    book_id: str

class PayFineRequest(BaseModel):
    fine_id: int

# ============ 登录认证相关路由 ============

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

# ============ 图书与读者查询 API ============

# 1. 搜索图书
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

# 2. 获取所有在馆图书
@app.get("/api/books/all")
async def get_all_books(db: AsyncSession = Depends(get_db)):
    stmt = select(Book).where(Book.现有库存 > 0)
    result = await db.execute(stmt)
    books = result.scalars().all()
    return [{"图书编号": b.图书编号, "书名": b.书名, "现有库存": b.现有库存} for b in books]

# 3. 获取所有读者
@app.get("/api/readers/all")
async def get_all_readers(db: AsyncSession = Depends(get_db)):
    stmt = select(Reader).order_by(Reader.读者编号)
    result = await db.execute(stmt)
    readers = result.scalars().all()
    return [
        {
            "读者编号": r.读者编号,
            "姓名": r.姓名,
            "已借数量": r.已借数量,
            "最大借阅量": r.最大借阅量,
            "联系电话": r.联系电话 or "未设置",
            "账号状态": r.账号状态
        }
        for r in readers
    ]

# ============ 核心借还业务 API ============

# 4. 借书业务（原触发器 1、2 逻辑已内置）
@app.post("/api/borrow")
async def borrow_book(req: BorrowRequest, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, req.book_id)
    if not book:
        return {"success": False, "message": "借阅失败：未找到该图书！"}

    reader = await db.get(Reader, req.reader_id)
    if not reader:
        return {"success": False, "message": "借阅失败：读者不存在！"}

    # 规则 1：账号冻结不能借书
    if reader.账号状态 == "冻结":
        return {"success": False, "message": "借阅失败：您的账号已被冻结！"}

    # 规则 2：达到借阅上限不能借书
    if reader.已借数量 >= reader.最大借阅量:
        return {"success": False, "message": f"借阅失败：您已达到最大借书数量限制（{reader.最大借阅量}本）！"}

    # 规则 3：图书库存不足不能借书
    if book.现有库存 <= 0:
        return {"success": False, "message": "借阅失败：该图书当前库存不足！"}

    try:
        new_record = BorrowRecord(
            读者编号=req.reader_id,
            图书编号=req.book_id,
            借出日期=date.today(),
            应还日期=date.today() + timedelta(days=30),
            记录状态="借阅中"
        )
        db.add(new_record)

        # 联动更新数量
        reader.已借数量 += 1
        book.现有库存 -= 1

        await db.commit()
        return {"success": True, "message": "借书成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"借书事务处理异常: {str(e)}")

# 5. 获取未还记录（增强版）
@app.get("/api/borrowings/active")
async def get_active_borrowings(db: AsyncSession = Depends(get_db)):
    today = date.today()
    stmt = (
        select(BorrowRecord)
        .options(joinedload(BorrowRecord.reader), joinedload(BorrowRecord.book))
        .where(BorrowRecord.归还日期.is_(None))
        .order_by(BorrowRecord.应还日期.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "记录编号": rec.记录编号,
            "读者编号": rec.读者编号,
            "姓名": rec.reader.姓名 if rec.reader else "未知读者",
            "联系电话": rec.reader.联系电话 if rec.reader else "",
            "图书编号": rec.图书编号,
            "书名": rec.book.书名 if rec.book else "未知图书",
            "作者": rec.book.作者 if rec.book else "",
            "借出日期": str(rec.借出日期),
            "应还日期": str(rec.应还日期),
            "是否逾期": rec.应还日期 < today
        }
        for rec in records
    ]

# 6. 还书业务（原触发器 3 逻辑与自动计罚已内置）
@app.post("/api/return")
async def return_book(req: ReturnRequest, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(BorrowRecord).where(
            BorrowRecord.读者编号 == req.reader_id,
            BorrowRecord.图书编号 == req.book_id,
            BorrowRecord.归还日期.is_(None)
        ).limit(1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return {"success": False, "message": "还书失败：未查到未还记录，请检查图书编号！"}

        reader = await db.get(Reader, req.reader_id)
        book = await db.get(Book, req.book_id)

        record.归还日期 = date.today()
        record.记录状态 = "已归还"

        # 联动恢复库存与借书额度
        if reader and reader.已借数量 > 0:
            reader.已借数量 -= 1
        if book:
            book.现有库存 += 1

        # 判断逾期并开具罚单
        if date.today() > record.应还日期:
            overdue_days = (date.today() - record.应还日期).days
            multa_amount = overdue_days * 1.5  # 每天 1.5 元

            new_fine = FineRecord(
                记录编号=record.记录编号,
                罚款金额=multa_amount,
                罚款原因="逾期还书",
                备注="未缴费"
            )
            db.add(new_fine)

            if reader:
                reader.账号状态 = "冻结"

            await db.commit()
            return {
                "success": True,
                "message": f"还书成功：检测到逾期 {overdue_days} 天，罚款 ￥{multa_amount:.2f} 已开具，账号已冻结。"
            }
        else:
            await db.commit()
            return {"success": True, "message": "还书成功：按期归还，库存与借阅额度已恢复。"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"还书业务处理失败: {str(e)}")

# ============ 罚款与维护 API ============

# 7. 获取未缴罚单
@app.get("/api/fines/unpaid")
async def get_unpaid_fines(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(FineRecord)
        .options(joinedload(FineRecord.borrowing).joinedload(BorrowRecord.reader))
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
        fine = await db.get(FineRecord, req.fine_id)
        if not fine:
            return {"success": False, "message": "罚单不存在！"}

        stmt = select(BorrowRecord).where(BorrowRecord.记录编号 == fine.记录编号)
        result = await db.execute(stmt)
        borrow = result.scalar_one_or_none()

        if not borrow:
            return {"success": False, "message": "关联的借阅记录不存在！"}

        reader_id = borrow.读者编号
        fine.备注 = "已缴费"

        # 检查该读者是否还有其他未缴罚单
        stmt_remain = select(FineRecord).join(BorrowRecord).where(
            BorrowRecord.读者编号 == reader_id,
            or_(FineRecord.备注 != "已缴费", FineRecord.备注.is_(None)),
            FineRecord.罚款编号 != fine.罚款编号
        )
        result_remain = await db.execute(stmt_remain)
        restantes = result_remain.scalars().all()

        if len(restantes) == 0:
            reader = await db.get(Reader, reader_id)
            if reader:
                reader.账号状态 = "正常"
            await db.commit()
            return {"success": True, "message": "缴费成功！名下罚单已全部结清，账号已恢复正常！"}
        else:
            await db.commit()
            return {"success": True, "message": f"缴费成功！但您仍有 {len(restantes)} 笔未结清，账号维持冻结。"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"缴费异常: {str(e)}")

# 9. 扫描逾期与冻结
@app.post("/api/admin/scan_and_freeze")
async def scan_and_freeze(db: AsyncSession = Depends(get_db)):
    try:
        today = date.today()
        # 扫描逾期
        stmt = select(BorrowRecord).where(
            BorrowRecord.归还日期.is_(None),
            BorrowRecord.应还日期 < today,
            BorrowRecord.记录状态 == "借阅中"
        )
        result = await db.execute(stmt)
        overdue_records = result.scalars().all()
        overdue_count = 0
        for record in overdue_records:
            record.记录状态 = "已逾期"
            overdue_count += 1

        # 查找违规读者并冻结
        overdue_reader_subquery = (
            select(BorrowRecord.读者编号)
            .where(BorrowRecord.归还日期.is_(None), BorrowRecord.应还日期 < today)
            .distinct()
        )
        unpaid_fine_subquery = (
            select(BorrowRecord.读者编号)
            .join(FineRecord, BorrowRecord.记录编号 == FineRecord.记录编号)
            .where(or_(FineRecord.备注 != "已缴费", FineRecord.备注.is_(None)))
            .distinct()
        )
        union_stmt = union(overdue_reader_subquery, unpaid_fine_subquery)
        stmt_violator = select(Reader).where(Reader.读者编号.in_(union_stmt), Reader.账号状态 == "正常")
        result_violator = await db.execute(stmt_violator)
        violators = result_violator.scalars().all()
        freeze_count = 0
        for reader in violators:
            reader.账号状态 = "冻结"
            freeze_count += 1

        await db.commit()
        return {
            "success": True,
            "message": f"✅ 逾期扫描完成！标记 {overdue_count} 条记录为逾期，冻结 {freeze_count} 个违规账号。"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"操作失败: {str(e)}")

# 10. 老赖名单
@app.get("/api/violators")
async def get_violators(db: AsyncSession = Depends(get_db)):
    stmt = select(Reader).where(Reader.账号状态 == "冻结")
    result = await db.execute(stmt)
    violators = result.scalars().all()
    return [{"姓名": v.姓名, "联系电话": v.联系电话, "账号状态": v.账号状态} for v in violators]

# 11. AI 推荐
@app.get("/api/recommend/{reader_id}")
async def recommend_books(reader_id: int):
    loop = asyncio.get_event_loop()
    recs = await loop.run_in_executor(executor, get_recommendations, reader_id)
    return recs

# 12. 获取所有图书分类
@app.get("/api/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(BookCategory)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return [{"类别编号": c.类别编号, "类别名称": c.类别名称} for c in categories]

# ============ 读者管理 API ============

# 13. 创建新读者
@app.post("/api/readers")
async def create_reader(request: Request, db: AsyncSession = Depends(get_db)):
    import re
    data = await request.json()
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    if not name or not phone:
        return {"success": False, "message": "姓名和手机号不能为空！"}
    if not re.match(r'^1\d{10}$', phone):
        return {"success": False, "message": "请输入有效的11位手机号！"}
    try:
        stmt = select(Reader).where(Reader.联系电话 == phone)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            return {"success": False, "message": "该手机号已被注册！"}
        new_reader = Reader(姓名=name, 联系电话=phone, 已借数量=0, 最大借阅量=5, 账号状态="正常")
        db.add(new_reader)
        await db.commit()
        return {"success": True, "message": f"✅ 读者 {name} 登记成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建读者失败: {str(e)}")

# 14. 修改读者手机号
@app.put("/api/readers/{reader_id}/phone")
async def update_reader_phone(reader_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    import re
    data = await request.json()
    new_phone = data.get("phone", "").strip()
    if not re.match(r'^1\d{10}$', new_phone):
        return {"success": False, "message": "请输入有效的11位手机号！"}
    stmt = select(Reader).where(Reader.联系电话 == new_phone, Reader.读者编号 != reader_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return {"success": False, "message": "该手机号已被其他读者使用！"}
    reader = await db.get(Reader, reader_id)
    if not reader:
        return {"success": False, "message": "读者不存在！"}
    reader.联系电话 = new_phone
    await db.commit()
    return {"success": True, "message": "✅ 手机号修改成功！"}

# 15. 注销读者
@app.delete("/api/readers/{reader_id}")
async def delete_reader(reader_id: int, db: AsyncSession = Depends(get_db)):
    reader = await db.get(Reader, reader_id)
    if not reader:
        return {"success": False, "message": "读者不存在！"}
    stmt = select(BorrowRecord).where(BorrowRecord.读者编号 == reader_id, BorrowRecord.归还日期.is_(None))
    result = await db.execute(stmt)
    if result.scalars().all():
        return {"success": False, "message": "该读者仍有未还图书，无法注销！"}
    await db.delete(reader)
    await db.commit()
    return {"success": True, "message": f"✅ 读者 {reader.姓名} 已成功注销！"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)