def recommendations(payload, factors=None):
    actions = []
    if str(payload.get('defaulted', 0)) == '1':
        actions.append('Prioritize a realistic repayment plan and avoid adding high-cost borrowing while existing obligations remain unresolved.')
    if str(payload.get('Loan_usage', 0)) == '1' or str(payload.get('Loan_informal', 0)) == '1':
        actions.append('Review active borrowing, compare repayment costs, and cap new informal or digital borrowing where possible.')
    if str(payload.get('accessto_13k_1month', 0)) == '0' or str(payload.get('saving_for_emergencies', 0)) == '0':
        actions.append('Build an emergency reserve gradually through small, regular savings contributions.')
    if str(payload.get('Savings_usage', 0)) == '0':
        actions.append('Consider starting a regular savings habit using an amount that is affordable for your current income situation.')
    if not actions:
        actions.append('Continue monitoring savings, borrowing, digital-finance use and emergency preparedness regularly.')
    return actions[:3]
