# app.py - 现代化 SQLAlchemy 2.0 ORM 版本
import os
import uvicorn
import asyncio
from datetime import date, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text
from sqlalchemy.orm import joinedload

# 导入 ORM 模型与数据库引擎
from database import engine, get_db, Book, Reader, BorrowRecord, FineRecord
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

# ============ 页面路由 ============
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# ============ ORM API 接口 ============

# 1. 搜索图书 (ORM 条件查询)
@app.get("/api/books/search")
async def search_books(keyword: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Book)
    if keyword:
        stmt = stmt.where(or_(Book.书名.like(f"%{keyword}%"), Book.作者.like(f"%{keyword}%")))
    else:
        stmt = stmt.limit(50)
    
    result = await db.execute(stmt)
    books = result.scalars().all()
    
    return [
        {
            "图书编号": b.图书编号,
            "书名": b.书名,
            "作者": b.作者 or "佚名",
            "出版社": b.出版社,
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

# 3. 获取所有正常读者
@app.get("/api/readers/all")
async def get_all_readers(db: AsyncSession = Depends(get_db)):
    stmt = select(Reader).where(Reader.账号状态 == "正常")
    result = await db.execute(stmt)
    readers = result.scalars().all()
    return [
        {
            "读者编号": r.读者编号,
            "姓名": r.姓名,
            "已借数量": r.已借数量,
            "最大借阅量": r.最大借阅量
        }
        for r in readers
    ]

# 4. 借书业务 (ORM 事务与实体修改)
@app.post("/api/borrow")
async def borrow_book(req: BorrowRequest, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, req.book_id)
    if not book or book.现有库存 <= 0:
        return {"success": False, "message": "借阅失败：该图书暂无在馆库存！"}

    reader = await db.get(Reader, req.reader_id)
    if not reader or reader.已借数量 >= reader.最大借阅量:
        return {"success": False, "message": "借阅失败：读者借阅数量已达上限！"}

    try:
        # 创建借阅记录
        new_record = BorrowRecord(
            读者编号=req.reader_id,
            图书编号=req.book_id,
            借出日期=date.today(),
            应还日期=date.today() + timedelta(days=30)
        )
        db.add(new_record)
        
        # 更新库存与借阅数
        book.现有库存 -= 1
        reader.已借数量 += 1
        
        await db.commit()
        return {"success": True, "message": "借书成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"事务处理异常: {str(e)}")

# 5. 获取未还记录 (关联查询 joinedload)
@app.get("/api/borrowings/active")
async def get_active_borrowings(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(BorrowRecord)
        .options(joinedload(BorrowRecord.reader), joinedload(BorrowRecord.book))
        .where(BorrowRecord.归还日期.is_(None))
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    return [
        {
            "读者编号": rec.reader.读者编号,
            "姓名": rec.reader.姓名,
            "图书编号": rec.book.图书编号,
            "书名": rec.book.书名
        }
        for rec in records if rec.reader and rec.book
    ]

# 6. 还书业务 (如果已有存储过程，可以通过 session.execute(text(...)) 执行)
@app.post("/api/return")
async def return_book(req: ReturnRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 执行还书存储过程
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
        .join(FineRecord.borrowing)
        .join(BorrowRecord.reader)
        .options(
            joinedload(FineRecord.borrowing).joinedload(BorrowRecord.reader)
        )
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

# 11. 老赖名单 (ORM 复合查询)
@app.get("/api/violators")
async def get_violators(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Reader)
        .join(Reader.borrowings)
        .join(BorrowRecord.fines)
        .where(
            and_(
                Reader.账号状态 == "冻结",
                or_(FineRecord.备注 != "已缴费", FineRecord.备注.is_(None))
            )
        )
        .distinct()
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

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)