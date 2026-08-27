"""
Business logic for billing_service.

create_booking_with_billing is the one function in this whole project where
transactional correctness actually matters: a booking must never exist
without its billing record, or vice versa.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from services.billing_service.models import Billing, Booking
from services.billing_service.schemas import BookingCreate


def create_booking_with_billing(db: Session, data: BookingCreate) -> tuple[Booking, Billing]:
    """
    Insert a Booking row and its matching Billing row as one atomic unit.

    Both objects are written in the same session/transaction and committed
    with a single db.commit() call. Atomicity comes from that single commit,
    not from the try/except below: until commit() succeeds, MySQL has not
    durably stored either row, so any failure before it leaves the database
    exactly as it was, with neither record present. Committing after each
    add() individually would NOT be atomic - the booking could survive a
    later billing failure.

    booking is flushed (sent to MySQL, but not committed) before billing is
    even constructed. billing.booking_id is a real FK into bookings, and
    there is no ORM relationship() linking the two models - so without this
    explicit flush, SQLAlchemy has no way to know booking's INSERT must run
    before billing's, and may emit them in the wrong order, which MySQL
    rejects (1452 FK violation) since billing_id would reference a row that
    doesn't exist yet. The flush is still inside the same transaction, so a
    later failure still rolls back the booking insert too.
    """
    now = datetime.now(timezone.utc)

    booking = Booking(
        booking_id=str(uuid.uuid4()),
        user_id=data.user_id,
        booking_type=data.booking_type,
        item_id=data.item_id,
        booking_date=now,
        status="confirmed",
    )

    try:
        db.add(booking)
        db.flush()

        billing = Billing(
            billing_id=str(uuid.uuid4()),
            user_id=data.user_id,
            booking_type=data.booking_type,
            booking_id=booking.booking_id,
            transaction_date=now,
            amount=data.amount,
            payment_method=data.payment_method,
            status="completed",
        )
        db.add(billing)
        db.commit()
    except Exception:
        # Nothing was durably written, but rollback() also resets the
        # session's internal state so it is safe to reuse for the next
        # query instead of staying stuck in a failed-transaction state.
        db.rollback()
        raise

    db.refresh(booking)
    db.refresh(billing)
    return booking, billing


def get_billing_by_id(db: Session, billing_id: str) -> Billing | None:
    return db.query(Billing).filter(Billing.billing_id == billing_id).first()


def list_billing_by_user(db: Session, user_id: str) -> list[Billing]:
    return db.query(Billing).filter(Billing.user_id == user_id).all()
