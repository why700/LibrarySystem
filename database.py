# database.py
import os
from datetime import date
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Date, ForeignKey, TEXT

# 数据库连接 URL（采用 asyncmy 驱动）
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "librarysystem")

DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@{DB_HOST}:3306/{DB_NAME}?charset=utf8mb4"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


class Base(DeclarativeBase):
    pass


# ============ ORM 模型映射 ============

class BookCategory(Base):
    __tablename__ = "图书类别"

    类别编号: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    类别名称: Mapped[str] = mapped_column(String(50), nullable=False)
    类别描述: Mapped[Optional[str]] = mapped_column(String(255))


class Book(Base):
    __tablename__ = "图书信息"

    图书编号: Mapped[str] = mapped_column(String(50), primary_key=True)
    书名: Mapped[str] = mapped_column(String(255), nullable=False)
    作者: Mapped[Optional[str]] = mapped_column(String(100))
    出版社: Mapped[Optional[str]] = mapped_column(String(100))
    简介: Mapped[Optional[str]] = mapped_column(TEXT)
    类别编号: Mapped[Optional[int]] = mapped_column(Integer)
    总库存: Mapped[int] = mapped_column(Integer, default=0)
    现有库存: Mapped[int] = mapped_column(Integer, default=0)

    borrowings: Mapped[list["BorrowRecord"]] = relationship(back_populates="book")


class Reader(Base):
    __tablename__ = "读者信息"

    读者编号: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    姓名: Mapped[str] = mapped_column(String(100), nullable=False)
    联系电话: Mapped[Optional[str]] = mapped_column(String(50))
    已借数量: Mapped[int] = mapped_column(Integer, default=0)
    最大借阅量: Mapped[int] = mapped_column(Integer, default=5)
    账号状态: Mapped[str] = mapped_column(String(20), default="正常")

    borrowings: Mapped[list["BorrowRecord"]] = relationship(back_populates="reader")


class BorrowRecord(Base):
    __tablename__ = "借阅记录"

    记录编号: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    读者编号: Mapped[int] = mapped_column(ForeignKey("读者信息.读者编号"), nullable=False)
    图书编号: Mapped[str] = mapped_column(ForeignKey("图书信息.图书编号"), nullable=False)
    借出日期: Mapped[date] = mapped_column(Date, default=date.today)
    应还日期: Mapped[date] = mapped_column(Date, nullable=False)
    归还日期: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    reader: Mapped["Reader"] = relationship(back_populates="borrowings")
    book: Mapped["Book"] = relationship(back_populates="borrowings")
    fines: Mapped[list["FineRecord"]] = relationship(back_populates="borrowing")


class FineRecord(Base):
    __tablename__ = "罚款记录"

    罚款编号: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    记录编号: Mapped[int] = mapped_column(ForeignKey("借阅记录.记录编号"), nullable=False)
    罚款金额: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    罚款原因: Mapped[Optional[str]] = mapped_column(String(255))
    备注: Mapped[Optional[str]] = mapped_column(String(50), default="未缴费")

    borrowing: Mapped["BorrowRecord"] = relationship(back_populates="fines")