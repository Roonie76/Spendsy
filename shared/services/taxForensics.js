// correct code
import { TAX_CONSTANTS } from '../config/constants';

export const TaxForensics = {
    // 1. THE INCOME AUDIT (Reconciliation)
    // Checks if Total Bank Credits match Salary Slips
    auditIncome: (transactions, profile) => {
        const salaryCredits = transactions
            .filter(t => t.type === 'income' && (t.category === 'salary' || t.description.toLowerCase().includes('salary')))
            .reduce((sum, t) => sum + t.amount, 0);

        const declaredSalary = parseFloat(profile.monthlyIncome || 0) * 12;
        
        // Tolerance of 10% (Variable pay/Bonus)
        const deviation = Math.abs(salaryCredits - declaredSalary);
        const integrityScore = deviation < (declaredSalary * 0.1) ? 100 : Math.max(0, 100 - (deviation / declaredSalary * 100));

        return {
            detected: salaryCredits,
            declared: declaredSalary,
            gap: declaredSalary - salaryCredits,
            status: integrityScore > 90 ? 'CLEAN' : integrityScore > 70 ? 'MISMATCH' : 'HIGH_RISK',
            integrityScore
        };
    },

    // 2. THE 80C "PROOF" CHECK
    // Verifies if money actually left the account for claimed deductions
    verifyInvestments: (transactions, deductions) => {
        const investmentKeywords = ['ppf', 'lic', 'elss', 'provident', 'life insurance', 'sukanya', 'tuition'];
        
        const proven80C = transactions
            .filter(t => t.type === 'expense' && investmentKeywords.some(k => t.description.toLowerCase().includes(k)))
            .reduce((sum, t) => sum + t.amount, 0);

        // We also assume EPF is deducted from salary before hitting bank, 
        // so we verify standard EPF (12% of Basic, approx 40% of Gross)
        const estimatedEPF = (parseFloat(deductions.grossSalary) * 0.40) * 0.12; 
        
        const totalProven = proven80C + estimatedEPF;
        const claimed = parseFloat(deductions.section80C || 0);

        return {
            claimed,
            proven: totalProven,
            gap: Math.max(0, claimed - totalProven),
            isFraudulent: claimed > (totalProven * 1.5) // If claiming 50% more than visible flows
        };
    },

    // 3. HRA CALCULATOR (The Real Rule)
    // Min(Actual HRA, Rent - 10% Basic, 50% Basic)
    calculateHRAExemption: (basicSalary, hraReceived, rentPaid, isMetro = true) => {
        if (rentPaid <= 0) return 0;

        const rule1 = hraReceived;
        const rule2 = rentPaid - (basicSalary * 0.10);
        const rule3 = basicSalary * (isMetro ? 0.50 : 0.40);

        return Math.max(0, Math.min(rule1, rule2, rule3));
    },

    // 4. ANOMALY DETECTOR
    // Detects cash deposits or huge unexplained credits
    detectAnomalies: (transactions) => {
        const highValueLimit = 200000; // SFT Reporting Limit
        const cashDeposits = transactions.filter(t => t.type === 'income' && t.description.toLowerCase().includes('cash deposit'));
        const highValueTxns = transactions.filter(t => t.amount >= highValueLimit);

        return {
            cashCount: cashDeposits.length,
            cashTotal: cashDeposits.reduce((s, t) => s + t.amount, 0),
            highValueCount: highValueTxns.length,
            flags: [
                ...cashDeposits.map(t => ({ severity: 'HIGH', msg: `Cash Deposit of ₹${t.amount} detected on ${new Date(t.date).toLocaleDateString()}` })),
                ...highValueTxns.map(t => ({ severity: 'MEDIUM', msg: `High Value Txn ₹${t.amount} - May trigger SFT reporting` }))
            ]
        };
    }
};