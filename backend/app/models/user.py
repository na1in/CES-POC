import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped

from app.models.base import Base


class UserRole(str, enum.Enum):
    analyst = "analyst"
    investigator = "investigator"
    director = "director"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = Column(String, primary_key=True)
    name: Mapped[str] = Column(String, nullable=False)
    email: Mapped[str] = Column(String, nullable=False, unique=True)
    role: Mapped[UserRole] = Column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    created_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
