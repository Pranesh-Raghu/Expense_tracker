from datetime import datetime

from fastapi import HTTPException

MIN_YEAR = 1900
MAX_YEAR = 9999


def _validate_year(year) -> None:
    if year is None:
        raise HTTPException(status_code=400, detail="Year is required.")
    if not (MIN_YEAR <= year <= MAX_YEAR):
        raise HTTPException(status_code=400, detail=f"Year must be between {MIN_YEAR} and {MAX_YEAR}.")


def _validate_month(month) -> None:
    if month is None:
        raise HTTPException(status_code=400, detail="Month is required.")
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12.")


def date_month_year_validator(date, month, year):
    """`date` here means day-of-month, not a `date` object - kept as-is
    (not renamed to `day`) to match every existing call site's positional
    argument order."""
    _validate_year(year)
    _validate_month(month)
    if date is None:
        raise HTTPException(status_code=400, detail="Date is required.")
    # A plain 1-31 range check on `date` alone can't catch Feb 30, Apr 31,
    # or a non-leap Feb 29 - only the actual year/month/day combination
    # determines whether the date exists. Constructing it is the simplest
    # way to reuse Python's own calendar rules instead of duplicating them,
    # and turns what would otherwise be an unhandled 500 in
    # models/expense_model.py's datetime(year, month, date) calls into a
    # clean 400 here.
    try:
        datetime(year, month, date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {exc}") from exc


def month_year_validator(month, year):
    _validate_year(year)
    _validate_month(month)


def year_validator(year):
    _validate_year(year)


def user_validator(user):
    if user is None:
        raise HTTPException(status_code=401, detail='authentication failed')


def expense_id_validator(expense_id):
    if expense_id is None:
        raise HTTPException(status_code=400, detail="Expense ID is required.")
