from sqlalchemy import Integer, Float, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import   Mapped, mapped_column
from datetime import datetime, timedelta
from database import Base, SessionLocal
from enums.expense_enums import ExpenseCategory,TransactionType
from auth import user_dependency


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), default=ExpenseCategory.FOOD, nullable=False)
    transaction: Mapped[TransactionType] = mapped_column(Enum(TransactionType), default=TransactionType.CREDIT, nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    @staticmethod
    def get_expenses(user:user_dependency):
        with SessionLocal() as db:

            return db.query(Expense).filter(Expense.user_id == user.get('id')).all()

    @staticmethod
    def get_expenses_by_ids(expense_ids: list[int]):
        """Fetch a specific set of expenses by id, in whatever order the DB
        returns them - callers that need permission-scoped access (owner,
        shared, or admin) compute the allowed id set via authz first."""
        if not expense_ids:
            return []
        with SessionLocal() as db:
            return db.query(Expense).filter(Expense.id.in_(expense_ids)).all()

    @staticmethod
    def get_expense_by_id(user: user_dependency,expense_id: int):
        with SessionLocal() as db:

            expense = db.query(Expense).filter(Expense.id == expense_id).first()

            return expense
    
    @staticmethod
    def create_expense(user: user_dependency,expense_data):
        with SessionLocal() as db:
         try:    
             last_expense = db.query(Expense).order_by(Expense.id.desc()).first()
             new_id = last_expense.id + 1 if last_expense else 1 
 
             expense = Expense(id = new_id,
                              amount = expense_data.amount,
                              category= expense_data.category,
                              transaction = expense_data.transaction,
                              user_id=user.get('id')
                              )
             db.add(expense)
             db.commit()
             db.refresh(expense)
             return expense
        
         except Exception as e:
             db.rollback()
             raise e
    
    @staticmethod
    def update_expense(user: user_dependency,expense_id:int,expense_data:dict):
        # No user_id filter here on purpose: an editor (via sharing) or an
        # org admin may update an expense they don't own. Whether the
        # calling user is actually allowed to is checked by authz in
        # services/expense_services.py before this is ever called.
        with SessionLocal() as db:
            expense = db.query(Expense).filter(Expense.id == expense_id).first()

            if not expense:
                return None
            
            if 'amount' in expense_data:
                expense.amount = expense_data['amount']
            
            if 'category' in expense_data:
                expense.category = expense_data['category']
            
            if 'transaction' in expense_data:
                expense.transaction = expense_data['transaction']
                
            db.commit()
            db.refresh(expense)
            
            return expense
            
    @staticmethod
    def delete_expense(user: user_dependency,expense_id:int):
        with SessionLocal() as db:
        
            expense = db.query(Expense).filter(Expense.id == expense_id).first()
            
            if not expense:
                return None
            
            db.delete(expense)
            db.commit()
            
            return expense
            
                          
    @staticmethod
    def get_expense_category(user: user_dependency):
        with SessionLocal() as db:

            return db.query(Expense.category).all()
            
    
    @staticmethod
    def get_monthly_reports(user: user_dependency, month, year):
        with SessionLocal() as db:
           start_date = datetime(year, month, 1)
           if month == 12:
            end_date = datetime(year + 1, 1, 1)
           else:
            end_date = datetime(year, month + 1, 1)

           report = db.query(Expense).filter(
            Expense.time >= start_date,
            Expense.time < end_date
             ).filter(Expense.user_id == user.get('id')).all()

           return report        
    
    @staticmethod
    def get_daily_reports(user: user_dependency,day, month, year):
                   
        start_date = datetime(year, month, day)
        end_date = start_date + timedelta(days=1)  
        with SessionLocal() as db:
           
           report = db.query(Expense).filter(
            Expense.time >= start_date,
            Expense.time < end_date
             ).filter(Expense.user_id == user.get('id')).all()

           return  report or []        
       
    @staticmethod
    def get_yearly_reports(user: user_dependency, year: int):
        with SessionLocal() as db:
            
          start_date = datetime(year, 1, 1) 
          end_date = datetime(year + 1, 1, 1)  

          report = (
            db.query(Expense)
            .filter(Expense.time >= start_date, Expense.time < end_date).filter(Expense.user_id == user.get('id'))
            .all()
        )

        return  report  
    
    @staticmethod
    def get_expenses_by_category(user: user_dependency,category: str):
        with SessionLocal() as db:
            expenses = db.query(Expense).filter(Expense.category == category).all()
        return expenses if expenses else []
     
    @staticmethod
    def get_expenses_by_transaction(user: user_dependency,transaction: str):
        with SessionLocal() as db:
            expenses = db.query(Expense).filter(Expense.transaction == transaction).all()
        return expenses if expenses else []
    
    
    @staticmethod
    def get_weekly_report(user: user_dependency,date,month,year):
        current_date = datetime(year, month, date)

    
        start_of_week = current_date - timedelta(days=current_date.weekday())

        with SessionLocal() as db:
            report = db.query(Expense).filter(
                Expense.time >= start_of_week,
                Expense.time <= current_date).filter(
                Expense.user_id == user.get('id')
            ).all()

            return  report
            
    
    
    @staticmethod
    def get_monthly_amount(user: user_dependency, month, year):
        
        start_date = datetime(year, month, 1)
        end_date = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        with SessionLocal() as db:
            total = db.query(func.sum(Expense.amount)).filter(
                Expense.time >= start_date,
                Expense.time < end_date,
                Expense.user_id == user.get('id')  
            ).scalar() or 0  
    
            return {
            "month": month,
            "year": year,
            "total_expense": total
        }
    
    
    @staticmethod
    def get_yearly_amount(user: user_dependency,year):
        
        start_date = datetime(year, 1, 1) 
        end_date = datetime(year + 1, 1, 1)
        
        with SessionLocal() as db:
            total = db.query(func.sum(Expense.amount)).filter(
                Expense.time >= start_date,
                Expense.time < end_date,
                Expense.user_id == user.get('id')
            ).scalar() or 0
            
            return{
                "year": year,
                "total_expense": total
            }
    
            
    @staticmethod
    def get_daily_amount(user: user_dependency, year: int, month: int, date: int):
        start_date = datetime(year, month, date)
        end_date = start_date + timedelta(days=1)  
        
        with SessionLocal() as db:
            total = db.query(func.sum(Expense.amount)).filter(
                Expense.time >= start_date,
                Expense.time < end_date,
                Expense.user_id == user.get('id')
            ).scalar() or 0
            
            return{
                "year": year,
                "month": month,
                "date": date,
                "total_expense": total
            }
            
    @staticmethod
    def get_weekly_amount(user: user_dependency, year, month, date):
        current_date = datetime(year, month, date)

        start_of_week = current_date - timedelta(days=current_date.weekday())

        with SessionLocal() as db:
            total = db.query(func.sum(Expense.amount)).filter(
                Expense.time >= start_of_week,
                Expense.time <= current_date,
                Expense.user_id == user.get('id')
            ).scalar() or 0

            return {
                "year": year,
                "month": month,
                "date": date,
                "total_expense": total
            }
