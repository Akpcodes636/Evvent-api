from sqlmodel import SQLModel

from database.session import engine
from model.booking import Order, Payment, Payout
from model.event import Category, Event, EventCategoryLink, EventImage, TicketType, UserCategoryPreference
from model.user import PasswordResetToken, RefreshToken, User


def init_db():
    SQLModel.metadata.create_all(engine)
