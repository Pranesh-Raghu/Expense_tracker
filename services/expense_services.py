from fastapi import HTTPException
from models.expense_model import Expense,ExpenseCategory, TransactionType, user_dependency
from schemas.expense_schemas import ExpenseCreate, ExpenseUpdate, ExpensePermissions
from services.expense_services import user_dependency  # noqa: F811
from validators.expense_validators import date_month_year_validator, month_year_validator,year_validator,user_validator,expense_id_validator
from authz import service as authz
import webhooks


def _attach_permissions(user_id: int, expense):
    # ExpenseResponse requires `permissions`, but it isn't a column on the
    # Expense model - compute it from authz and hang it off the instance so
    # response_model serialization picks it up like any other attribute.
    expense.permissions = ExpensePermissions(
        can_edit=authz.can_edit(user_id, expense.id),
        can_delete=authz.can_delete(user_id, expense.id),
        can_share=authz.can_share(user_id, expense.id),
    )
    return expense


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

    return [_attach_permissions(user.get('id'), e) for e in expenses]


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
    
    report = Expense.get_monthly_reports(user,month,year)
    
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

def get_yearly_reports(user:user_dependency,year):
    
    user_validator(user)
    
    year_validator(year)
    
    report = Expense.get_yearly_reports(user,year)
    
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

def get_expenses_by_category(user: user_dependency,category):
    
    user_validator(user)
        
    if category is None:
        raise HTTPException(status_code=400, detail="Category is requird.")
    
    expenses = Expense.get_expenses_by_category(user,category)
    
    if expenses is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return expenses

def get_expenses_by_transaction(user: user_dependency,transaction):
    
    user_validator(user)
             
    if transaction is None:
        raise HTTPException(status_code=400, detail="Transaction is requird.")        
    
    expenses = Expense.get_expenses_by_transaction(user,transaction)
    
    if expenses is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return expenses

def get_monthly_amount(user:user_dependency,month,year):
    user_validator(user)
     
    month_year_validator(month,year) 

    report = Expense.get_monthly_amount(user,month,year)
    
    if report is None:
        raise HTTPException(status_code=404, detail="Amount not found")
    
    return report

def get_yearly_amount(user: user_dependency,year):
    user_validator(user)
    
    year_validator(year)
    
    amount = Expense.get_yearly_amount(user,year)
    
    if amount is None:
        raise HTTPException(status_code=404, detail="Amount not found")
    
    return amount


def get_daily_amount(user:user_dependency,year,month,date):
        user_validator(user)
        
        date_month_year_validator(date,month,year)
        
        report = Expense.get_daily_amount(user,year,month,date)
    
        if report is None:
          raise HTTPException(status_code=404, detail="Amount not found")
    
        return report

def get_daily_reports(user:user_dependency, day,month,year):
    
    user_validator(user)
    
    date_month_year_validator(day,month,year)
    
    report = Expense.get_daily_reports(user,day,month,year)
    
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

def get_weekly_reports(user:user_dependency, day,month,year):
    
    date_month_year_validator(day,month,year)
    
    report = Expense.get_weekly_report(user,day,month,year)
    
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


def get_weekly_amount(user: user_dependency,year,month,date):
    user_validator(user)
     
    date_month_year_validator(date,month,year)
    
    amount = Expense.get_weekly_amount(user,year,month,date)
    
    return amount

