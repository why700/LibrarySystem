# routers/books.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Book, BookCategory
from recommend import get_recommendations

router = APIRouter(prefix="/api", tags=["图书与推荐"])
executor = ThreadPoolExecutor(max_workers=4)

@router.get("/books/search")
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

@router.get("/books/all")
async def get_all_books(db: AsyncSession = Depends(get_db)):
    stmt = select(Book).where(Book.现有库存 > 0)
    result = await db.execute(stmt)
    books = result.scalars().all()
    return [{"图书编号": b.图书编号, "书名": b.书名, "现有库存": b.现有库存} for b in books]

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(BookCategory)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return [{"类别编号": c.类别编号, "类别名称": c.类别名称} for c in categories]

@router.get("/recommend/{reader_id}")
async def recommend_books(reader_id: int):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, get_recommendations, reader_id)