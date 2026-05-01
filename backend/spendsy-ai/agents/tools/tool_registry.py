from .create_plan import create_plan
from .adjust_plan import adjust_plan
from .create_loan_repayment_plan import create_loan_repayment_plan
from .update_tax_profile import update_tax_profile
from .compare_tax_regimes import compare_tax_regimes, simulate_tax_whatif
from .simulate_loan_repayment import simulate_loan_repayment
from .simulate_tax_efficient_investment import simulate_tax_efficient_investment_plan
from .sync_credit_card_payments import sync_credit_card_payments
from .get_transactions import get_transactions
from .query_spending_data import query_spending_data
from .search_internet import search_internet

def get_tool_registry():
    """Returns a dictionary mapping tool names to functions."""
    return {
        "create_plan": create_plan,
        "adjust_plan": adjust_plan,
        "create_loan_repayment_plan": create_loan_repayment_plan,
        "update_tax_profile": update_tax_profile,
        "compare_tax_regimes": compare_tax_regimes,
        "simulate_tax_whatif": simulate_tax_whatif,
        "simulate_loan_repayment": simulate_loan_repayment,
        "simulate_tax_efficient_investment": simulate_tax_efficient_investment_plan,
        "sync_credit_card_payments": sync_credit_card_payments,
        "get_transactions": get_transactions,
        "query_spending_data": query_spending_data,
        "search_internet": search_internet
    }
