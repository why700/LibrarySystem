# routers/fines.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

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

@router.post("/pay_fine")
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