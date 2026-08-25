# routers/readers.py
import re
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Reader, BorrowRecord

router = APIRouter(prefix="/api", tags=["读者管理"])

@router.get("/readers/all")
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

@router.post("/readers")
async def create_reader(request: Request, db: AsyncSession = Depends(get_db)):
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

@router.put("/readers/{reader_id}/phone")
async def update_reader_phone(reader_id: int, request: Request, db: AsyncSession = Depends(get_db)):
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

@router.delete("/readers/{reader_id}")
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