# routers/borrow.py
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Book, Reader, BorrowRecord, FineRecord

router = APIRouter(prefix="/api", tags=["借还业务"])

class BorrowRequest(BaseModel):
    reader_id: int
    book_id: str

class ReturnRequest(BaseModel):
    reader_id: int
    book_id: str

@router.post("/borrow")
async def borrow_book(req: BorrowRequest, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, req.book_id)
    if not book:
        return {"success": False, "message": "借阅失败：未找到该图书！"}

    reader = await db.get(Reader, req.reader_id)
    if not reader:
        return {"success": False, "message": "借阅失败：读者不存在！"}

    if reader.账号状态 == "冻结":
        return {"success": False, "message": "借阅失败：您的账号已被冻结！"}
    if reader.已借数量 >= reader.最大借阅量:
        return {"success": False, "message": f"借阅失败：您已达到最大借书数量限制（{reader.最大借阅量}本）！"}
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
        reader.已借数量 += 1
        book.现有库存 -= 1
        await db.commit()
        return {"success": True, "message": "借书成功！"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"借书事务处理异常: {str(e)}")

@router.get("/borrowings/active")
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

# routers/borrow.py 内部的 return_book 函数

# routers/borrow.py
@router.post("/return")
async def return_book(req: ReturnRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. 查找对应的未还借阅记录
        stmt = select(BorrowRecord).where(
            BorrowRecord.读者编号 == req.reader_id,
            BorrowRecord.图书编号 == req.book_id,
            BorrowRecord.归还日期.is_(None)
        ).limit(1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return {"success": False, "message": "还书失败：未查到该借阅记录，请确认是否已归还！"}

        reader = await db.get(Reader, req.reader_id)
        book = await db.get(Book, req.book_id)

        # 2. 更新借阅记录状态
        record.归还日期 = date.today()
        record.记录状态 = "已归还"

        # 3. 恢复在馆库存与已借数量
        if reader and reader.已借数量 > 0:
            reader.已借数量 -= 1
        if book:
            book.现有库存 += 1

        # 4. 判断逾期
        if date.today() > record.应还日期:
            overdue_days = (date.today() - record.应还日期).days
            multa_amount = round(overdue_days * 1.5, 2)

            # ✅ 核心修复：检查是否已有罚款记录（防 Duplicate entry '12' 冲突）
            stmt_fine = select(FineRecord).where(FineRecord.记录编号 == record.记录编号)
            fine_result = await db.execute(stmt_fine)
            existing_fine = fine_result.scalar_one_or_none()

            if existing_fine:
                existing_fine.罚款金额 = multa_amount
                existing_fine.罚款原因 = f"逾期还书（超期 {overdue_days} 天）"
                existing_fine.备注 = "未缴费"
            else:
                new_fine = FineRecord(
                    记录编号=record.记录编号,
                    罚款金额=multa_amount,
                    罚款原因=f"逾期还书（超期 {overdue_days} 天）",
                    备注="未缴费"
                )
                db.add(new_fine)

            # 读者账号设为冻结
            if reader:
                reader.账号状态 = "冻结"

            await db.commit()
            return {
                "success": True,
                "message": f"还书成功！检测到逾期 {overdue_days} 天，已生成/更新 ￥{multa_amount} 罚单，账号处于冻结状态（请前往缴纳罚金）。"
            }
        else:
            await db.commit()
            return {"success": True, "message": "还书成功！按期归还，库存与借阅额度已恢复。"}

    except Exception as e:
        await db.rollback()
        return {"success": False, "message": f"还书业务处理失败: {str(e)}"}