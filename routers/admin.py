# routers/admin.py
from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, or_, union
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, Reader, BorrowRecord, FineRecord

router = APIRouter(prefix="/api", tags=["系统维护"])

@router.post("/admin/scan_and_freeze")
async def scan_and_freeze(db: AsyncSession = Depends(get_db)):
    try:
        today = date.today()
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

@router.get("/violators")
async def get_violators(db: AsyncSession = Depends(get_db)):
    stmt = select(Reader).where(Reader.账号状态 == "冻结")
    result = await db.execute(stmt)
    violators = result.scalars().all()
    return [{"姓名": v.姓名, "联系电话": v.联系电话, "账号状态": v.账号状态} for v in violators]