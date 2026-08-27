"""
Shared validation rules used across services.

Why this lives in `common/` instead of each service: user_id (SSN format),
state, and zip validation are needed only by user_service today, but keeping
them here means any future service that touches user data reuses the exact
same rule instead of re-implementing (and possibly getting subtly wrong) its
own regex.

Custom exceptions (instead of raising ValueError everywhere) let route code
catch a specific failure and map it to the correct HTTP status and message,
without parsing error text to figure out what went wrong.
"""

import re

# --- Custom exceptions -----------------------------------------------------
# Each one names a single, specific failure. A route handler can catch
# InvalidUserIdError and return 400, or DuplicateUserError and return 409,
# without inspecting a message string.


class InvalidUserIdError(Exception):
    """Raised when user_id does not match the SSN format ###-##-####."""


class DuplicateUserError(Exception):
    """Raised when a user_id already exists in the database."""


class MalformedStateError(Exception):
    """Raised when state is not a valid two-letter US state abbreviation."""


class MalformedZipError(Exception):
    """Raised when zip_code does not match ##### or #####-####."""


# --- Validation rules --------------------------------------------------------

USER_ID_PATTERN = re.compile(r"^\d{3}-\d{2}-\d{4}$")
ZIP_PATTERN = re.compile(r"^\d{5}(-\d{4})?$")

# All 50 states plus DC, as two-letter USPS abbreviations. A fixed set is
# used (not a regex) because "is this a real state" is a membership check,
# not a pattern - "ZZ" matches a two-letter pattern but isn't a state.
VALID_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def validate_user_id(user_id: str) -> None:
    """Raise InvalidUserIdError unless user_id matches ###-##-####."""
    if not USER_ID_PATTERN.match(user_id):
        raise InvalidUserIdError(
            f"user_id '{user_id}' must match the format ###-##-####"
        )


def validate_state(state: str) -> None:
    """Raise MalformedStateError unless state is a valid US abbreviation."""
    if state.upper() not in VALID_US_STATES:
        raise MalformedStateError(
            f"state '{state}' is not a valid US state abbreviation"
        )


def validate_zip_code(zip_code: str) -> None:
    """Raise MalformedZipError unless zip_code matches ##### or #####-####."""
    if not ZIP_PATTERN.match(zip_code):
        raise MalformedZipError(
            f"zip_code '{zip_code}' must match ##### or #####-####"
        )
