from fastapi import APIRouter, status
from schemas.expense_schemas import ExpenseCreate, ExpenseResponse, ExpenseUpdate,ExpenseCategoryResponse,ExpenseTransactionRespone,ExpenseReport,MonthlyExpenseAmount,DailyExpenseAmount, YearlyExpenseAmount, ShareExpenseRequest, MessageResponse
from services import expense_services
from models.expense_model import user_dependency
from typing import List
router = APIRouter()


@router.get("/", response_model=list[ExpenseResponse], status_code=status.HTTP_200_OK)
def get__all__expenses(user:user_dependency):
    return expense_services.get_all_expenses(user)


#  ":int" constrains this segment to digits only, so a literal path like
# /categories or /transactions below can never accidentally match here -
# without it, Starlette matches *any* single path segment (since it's
# registered first) and FastAPI's own int coercion of expense_id then fails
# with a confusing 422, instead of falling through to the intended route.
# See frontend/src/api/endpoints/expenses.ts for the workaround this let the
# frontend drop.
@router.get("/{expense_id:int}",response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
def get__expense__by__id(user: user_dependency,expense_id:int):
    return expense_services.get_expense_by_id(user,expense_id)


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create__expense(user:user_dependency, expense: ExpenseCreate):
    return expense_services.create_expense(user,expense)


@router.put("/{expense_id:int}",response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
def update__expense(user: user_dependency,expense_id:int,expense_data: ExpenseUpdate):
    return expense_services.update_expense(user,expense_id,expense_data)


@router.delete("/{expense_id:int}", response_model=ExpenseResponse, status_code=status.HTTP_200_OK)
def delete__expense(user:user_dependency,expense_id: int):
    return expense_services.delete_expense(user,expense_id)

@router.post("/{expense_id:int}/share", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def share__expense(user: user_dependency, expense_id: int, share_data: ShareExpenseRequest):
    return expense_services.share_expense(user, expense_id, share_data.target_user_id, share_data.relation)

@router.delete("/{expense_id:int}/share/{target_user_id:int}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def unshare__expense(user: user_dependency, expense_id: int, target_user_id: int):
    return expense_services.unshare_expense(user, expense_id, target_user_id)

@router.get("/categories/", response_model=ExpenseCategoryResponse, status_code=status.HTTP_200_OK)
def expenses__categories(user:user_dependency):
    categories =  expense_services.expense_categories(user)
    return categories
    
@router.get("/transactions/", response_model=ExpenseTransactionRespone, status_code=status.HTTP_200_OK)
def expenses_transaction_types(user:user_dependency):
    transactions = expense_services.expense_transaction_types(user)
    return transactions    

@router.get("/monthlyreport/{year}/{month}",response_model=List[ExpenseReport], status_code=status.HTTP_200_OK)
def get_monthly__reports(user:user_dependency,month: int,year: int):
    expense = expense_services.get_monthly_reports(user,month,year)
    return expense

@router.get("/monthlyreport/{year}",response_model=List[ExpenseReport], status_code=status.HTTP_200_OK)
def get_yearly__reports(user:user_dependency,year:int):
    expense = expense_services.get_yearly_reports(user,year)
    return expense

@router.get("/dailyreport/{year}/{month}/{day}", response_model=List[ExpenseReport], status_code=status.HTTP_200_OK)
def get__daily__report(user:user_dependency,day: int,month:int,year: int):
    amount = expense_services.get_daily_reports(user,day,month,year)
    return amount

@router.get("/weeklyreport/{year}/{month}/{day}", response_model=List[ExpenseReport], status_code=status.HTTP_200_OK)
def get__weekly__report(user:user_dependency,day:int,month: int,year: int):
    report = expense_services.get_weekly_reports(user,day,month,year)
    return report
    

@router.get("/transactions/{transaction}", response_model=List[ExpenseResponse], status_code=status.HTTP_200_OK)
def get__expenses__by__transaction(user: user_dependency,transaction: str):
    expense = expense_services.get_expenses_by_transaction(user,transaction)
    return expense

@router.get("/categories/{category}", response_model=List[ExpenseResponse], status_code=status.HTTP_200_OK)
def get__expenses_by_category(user: user_dependency,category: str):
    expense = expense_services.get_expenses_by_category(user,category)
    return expense

@router.get("/monthlyreport/{year}/{month}/amount", response_model=MonthlyExpenseAmount, status_code=status.HTTP_200_OK)
def get__monthly__amount(user:user_dependency,month: int,year: int):
    amount = expense_services.get_monthly_amount(user,month,year)
    return amount

    
@router.get("/dailyreport/{year}/{month}/{day}/amount", response_model=DailyExpenseAmount, status_code=status.HTTP_200_OK)
def get__daily__amount(user:user_dependency,year: int,month:int,day: int):
    amount = expense_services.get_daily_amount(user,year,month,day)
    return amount
    
    
@router.get("/yearlyreport/{year}/amount",response_model=YearlyExpenseAmount, status_code=status.HTTP_200_OK)
def get_yearly__amount(user:user_dependency,year:int):
    expense = expense_services.get_yearly_amount(user,year)
    return expense


@router.get("/weeklyreport/{year}/{month}/{day}/amount", response_model=DailyExpenseAmount, status_code=status.HTTP_200_OK)
def get__weekly__amount(user:user_dependency,year: int,month:int,day: int):
    amount = expense_services.get_weekly_amount(user,year,month,day)
    return amount

