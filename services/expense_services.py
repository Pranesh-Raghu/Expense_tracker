from fastapi import HTTPException
from models.expense_model import Expense,ExpenseCategory, TransactionType, user_dependency
from schemas.expense_schemas import ExpenseCreate, ExpenseUpdate, ExpensePermissions
from validators.expense_validators import date_month_year_validator, month_year_validator,year_validator,user_validator,expense_id_validator
from authz import service as authz
import webhooks


def _attach_permissions(user_id: int, expense):
    # ExpenseResponse requires `permissions`, but it isn't a column on the
    # Expense model - compute it from authz and hang it off the instance so
    # response_model serialization picks it up like any other attribute.
    # Only for single-expense paths (create/update/delete/get-by-id) - a
    # list of N expenses uses _attach_permissions_bulk instead, since this
    # does 3 OpenFGA round trips per call.
    expense.permissions = ExpensePermissions(
        can_edit=authz.can_edit(user_id, expense.id),
        can_delete=authz.can_delete(user_id, expense.id),
        can_share=authz.can_share(user_id, expense.id),
    )
    return expense


def _attach_permissions_bulk(user_id: int, expenses):
    # Same result as calling _attach_permissions on every item, but 3
    # OpenFGA round trips total instead of 3 per expense - see
    # authz.bulk_expense_permissions. Listing a page of expenses shouldn't
    # cost O(N) network calls just to render each row's edit/delete/share
    # buttons.
    permission_sets = authz.bulk_expense_permissions(user_id)
    for expense in expenses:
        expense.permissions = ExpensePermissions(
            can_edit=expense.id in permission_sets["can_edit"],
            can_delete=expense.id in permission_sets["can_delete"],
            can_share=expense.id in permission_sets["can_share"],
        )
    return expenses


# Create Expense
def create_expense(user: user_dependency,expense_data: ExpenseCreate):

    user_validator(user)

    expense = Expense.create_expense(user,expense_data)

    authz.on_expense_created(owner_id=user.get('id'), expense_id=expense.id)
    webhooks.dispatch_event("expense.created", {"expense_id": expense.id, "user_id": user.get('id'), "amount": expense.amount})

    return _attach_permissions(user.get('id'), expense)


# Get all Expenses: everything the user owns, plus anything shared with them
# or visible via an admin role - authz is the single source of truth for
# which expense ids are visible, not a DB filter.
def get_all_expenses(user:user_dependency):

    user_validator(user)

    expense_ids = authz.list_viewable_expense_ids(user.get('id'))

    expenses = Expense.get_expenses_by_ids(expense_ids)

    return _attach_permissions_bulk(user.get('id'), expenses)


def get_expense_by_id(user: user_dependency,expense_id: int):

    user_validator(user)

    expense_id_validator(expense_id)

    expense = Expense.get_expense_by_id(user,expense_id)

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    authz.require(authz.can_view(user.get('id'), expense_id), "You don't have permission to view this expense")

    return _attach_permissions(user.get('id'), expense)


def update_expense(user: user_dependency,expense_id:int,expense_data: ExpenseUpdate):

    user_validator(user)

    expense_id_validator(expense_id)

    authz.require(authz.can_edit(user.get('id'), expense_id), "You don't have permission to edit this expense")

    expense = Expense.update_expense(user,expense_id,expense_data.model_dump(exclude_none=True))

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    webhooks.dispatch_event("expense.updated", {"expense_id": expense.id, "user_id": user.get('id')})

    return _attach_permissions(user.get('id'), expense)


def share_expense(user: user_dependency, expense_id: int, target_user_id: int, relation: str):
    user_validator(user)
    expense_id_validator(expense_id)

    if not Expense.get_expense_by_id(user, expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")

    authz.require(authz.can_share(user.get('id'), expense_id), "You don't have permission to share this expense")

    authz.share_expense(expense_id, target_user_id, relation)
    webhooks.dispatch_event("expense.shared", {
        "expense_id": expense_id, "shared_by_user_id": user.get('id'),
        "target_user_id": target_user_id, "relation": relation,
    })
    return {"message": f"Expense {expense_id} shared with user {target_user_id} as {relation}"}


def unshare_expense(user: user_dependency, expense_id: int, target_user_id: int):
    user_validator(user)
    expense_id_validator(expense_id)

    if not Expense.get_expense_by_id(user, expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")

    authz.require(authz.can_share(user.get('id'), expense_id), "You don't have permission to modify sharing on this expense")

    authz.unshare_expense(expense_id, target_user_id)
    return {"message": f"Removed user {target_user_id}'s access to expense {expense_id}"}


def delete_expense(user:user_dependency,expense_id: int):
    user_validator(user)

    expense_id_validator(expense_id)

    authz.require(authz.can_delete(user.get('id'), expense_id), "You don't have permission to delete this expense")

    expense = Expense.delete_expense(user,expense_id)

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Compute permissions before the authz tuples for this expense are torn
    # down - afterwards every check would read as False.
    _attach_permissions(user.get('id'), expense)

    authz.on_expense_deleted(expense_id)
    webhooks.dispatch_event("expense.deleted", {"expense_id": expense_id, "user_id": user.get('id')})

    return expense

def expense_categories(user:user_dependency):
    
    user_validator(user)
    
    return {"categories": list(ExpenseCategory)}

def expense_transaction_types(user:user_dependency):
    user_validator(user)
    
    return {"transaction": list(TransactionType)}


def get_monthly_reports(user:user_dependency,month,year):

    user_validator(user)

    month_year_validator(month,year)

    # Never None - always a (possibly empty) list for a month with no
    # expenses, which is a normal 200 response, not a 404.
    return Expense.get_monthly_reports(user,month,year)

def get_yearly_reports(user:user_dependency,year):

    user_validator(user)

    year_validator(year)

    return Expense.get_yearly_reports(user,year)

def get_expenses_by_category(user: user_dependency,category):

    user_validator(user)

    if category not in ExpenseCategory.__members__:
        raise HTTPException(status_code=400, detail=f"Unknown category: {category}")

    return Expense.get_expenses_by_category(user,category)

def get_expenses_by_transaction(user: user_dependency,transaction):

    user_validator(user)

    if transaction not in TransactionType.__members__:
        raise HTTPException(status_code=400, detail=f"Unknown transaction type: {transaction}")

    return Expense.get_expenses_by_transaction(user,transaction)

def get_monthly_amount(user:user_dependency,month,year):
    user_validator(user)

    month_year_validator(month,year)

    return Expense.get_monthly_amount(user,month,year)

def get_yearly_amount(user: user_dependency,year):
    user_validator(user)

    year_validator(year)

    return Expense.get_yearly_amount(user,year)


def get_daily_amount(user:user_dependency,year,month,date):
        user_validator(user)

        date_month_year_validator(date,month,year)

        return Expense.get_daily_amount(user,year,month,date)

def get_daily_reports(user:user_dependency, day,month,year):

    user_validator(user)

    date_month_year_validator(day,month,year)

    return Expense.get_daily_reports(user,day,month,year)

def get_weekly_reports(user:user_dependency, day,month,year):

    user_validator(user)

    date_month_year_validator(day,month,year)

    return Expense.get_weekly_report(user,day,month,year)


def get_weekly_amount(user: user_dependency,year,month,date):
    user_validator(user)
     
    date_month_year_validator(date,month,year)
    
    amount = Expense.get_weekly_amount(user,year,month,date)
    
    return amount

