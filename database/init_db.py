from sqlmodel import SQLModel

from database.session import engine
from model.booking import Order, Payment, Payout
from model.event import Category, Event, EventCategoryLink, EventImage, TicketType
from model.user import PasswordResetToken, User


def init_db():
    SQLModel.metadata.create_all(engine)
