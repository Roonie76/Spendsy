from .create_plan import create_plan
from .adjust_plan import adjust_plan
from .create_loan_repayment_plan import create_loan_repayment_plan

def get_tool_registry():
    """Returns a dictionary mapping tool names to functions."""
    return {
        "create_plan": create_plan,
        "adjust_plan": adjust_plan,
        "create_loan_repayment_plan": create_loan_repayment_plan
    }
