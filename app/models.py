from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Skill(db.Model):
    __tablename__ = "Skills"
    __table_args__ = {"autoload_with": db.engine}
    nid: Mapped[str] = mapped_column(String(50), primary_key=True)
