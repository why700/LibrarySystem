# routers/fines.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_db, Reader, BorrowRecord, FineRecord

router = APIRouter(prefix="/api", tags=["罚金业务"])

class PayFineRequest(BaseModel):
    fine_id: int

@router.get("/fines/unpaid")
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

# routers/fines.py
@router.post("/pay_fine")
async def pay_fine(req: PayFineRequest, db: AsyncSession = Depends(get_db)):
    try:
        # 1. 查找目标罚单
        fine = await db.get(FineRecord, req.fine_id)
        if not fine:
            return {"success": False, "message": "罚单不存在！"}

        stmt = select(BorrowRecord).where(BorrowRecord.记录编号 == fine.记录编号)
        result = await db.execute(stmt)
        borrow = result.scalar_one_or_none()
        if not borrow:
            return {"success": False, "message": "关联的借阅记录不存在！"}

        reader_id = borrow.读者编号
        # 标记已缴费
        fine.备注 = "已缴费"

        # 2. 检查读者是否还有其他【未缴罚单】
        stmt_remain_fine = select(FineRecord).join(BorrowRecord).where(
            BorrowRecord.读者编号 == reader_id,
            or_(FineRecord.备注 != "已缴费", FineRecord.备注.is_(None)),
            FineRecord.罚款编号 != fine.罚款编号
        )
        result_remain_fine = await db.execute(stmt_remain_fine)
        remaining_fines = result_remain_fine.scalars().all()

        # 3. 检查读者是否还有【逾期且未还的图书】
        today = date.today()
        stmt_overdue_book = select(BorrowRecord).where(
            BorrowRecord.读者编号 == reader_id,
            BorrowRecord.归还日期.is_(None),
            BorrowRecord.应还日期 < today
        )
        result_overdue_book = await db.execute(stmt_overdue_book)
        remaining_overdue_books = result_overdue_book.scalars().all()

        # 4. 只有既无欠款、也无逾期未还图书时，才解冻账号
        reader = await db.get(Reader, reader_id)
        if len(remaining_fines) == 0 and len(remaining_overdue_books) == 0:
            if reader:
                reader.账号状态 = "正常"
            await db.commit()
            return {"success": True, "message": "缴费成功！名下违规已全部结清，账号已自动恢复【正常】！"}
        elif len(remaining_fines) > 0:
            await db.commit()
            return {"success": True, "message": f"缴费成功！名下仍有 {len(remaining_fines)} 笔罚款未缴，账号保持冻结。"}
        else:
            await db.commit()
            return {"success": True, "message": f"缴费成功！但名下仍有 {len(remaining_overdue_books)} 本图书逾期未还，请先归还以解除冻结。"}

    except Exception as e:
        await db.rollback()
        return {"success": False, "message": f"缴费异常: {str(e)}"}