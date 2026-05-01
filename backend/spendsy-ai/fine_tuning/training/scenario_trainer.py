"""
TORA Scenario Trainer — Expanded v2
=====================================
42 scenario categories × 8 user archetypes = 336 training runs.

Research basis:
- Business Standard 2025: 33% of income goes to EMI; 46% borrow for phones/appliances
- IndiaInvestments wiki: top queries = SIP, CIBIL, home loan, tax regime, NPS vs EPF
- Wealth Munshi 2026: dual-goal planning (kids education + marriage) is top family query
- Reddit r/IndiaInvestments: rent vs buy, prepay loan vs invest, salary allocation
- Fintech State 2025: gig/freelancer financial instability, embedded credit, BNPL surge

Categories (14 total):
  1.  appliances       — fridge, AC, washing machine, TV
  2.  gadgets          — iPhone, laptop, camera, gaming PC
  3.  vehicle          — car, EV, scooter, used car
  4.  short_trip       — Goa, Coorg, Manali weekend
  5.  long_vacation    — Europe, Japan, Southeast Asia
  6.  medical          — emergency fund, surgery cost, health insurance
  7.  tax_saving       — 80C, ELSS, NPS, old vs new regime
  8.  home_buying      — first home, rent vs buy, down payment
  9.  education        — child education fund, own MBA, upskilling
  10. wedding          — own wedding, kid's wedding corpus
  11. retirement       — NPS vs EPF vs SIP, early retirement, corpus goal
  12. credit_repair    — CIBIL score low, too much CC debt, restructure
  13. salary_planning  — got hike, first job, salary allocation
  14. side_income      — freelance income, rental income, stock trading
"""
from __future__ import annotations

import sys, os, types, time, logging, json, math
from typing import Any, Optional

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("scenario_trainer")

# ── Mocks ─────────────────────────────────────────────────────────────────────
def _mock():
    for mod in ["playwright", "playwright.async_api"]:
        m = types.ModuleType(mod); m.async_playwright = None; sys.modules[mod] = m
    chroma = types.ModuleType("chromadb")
    class _Col:
        def count(self): return 0
        def add(self, *a, **k): pass
        def query(self, *a, **k): return {"documents":[[]],"metadatas":[[]],"distances":[[]]}
    chroma.PersistentClient = lambda *a,**k: type("C",(),{"get_or_create_collection":lambda s,*a,**k:_Col()})()
    sys.modules["chromadb"] = chroma
    for n in ["google","google.genai"]:
        m=types.ModuleType(n); m.Client=lambda*a,**k:None; sys.modules[n]=m
_mock()

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.dirname(_ROOT))

from agents.tora.reasoning.goal_decomposer import decompose_goal, GoalType
from agents.tora.reasoning.financial_reasoner import compute_strategies
from agents.tora.reasoning.strategy_ranker import rank_strategies
from agents.tora.reasoning.techniques import tag_techniques, build_technique_block
from fine_tuning.evaluator import evaluate
from fine_tuning.reasoning_store import save as store_save, get_index_stats
from fine_tuning.seed_traces import load_seed_traces


# ─────────────────────────────────────────────────────────────────────────────
# USER ARCHETYPES (8) — covers the full Indian earning population spectrum
# ─────────────────────────────────────────────────────────────────────────────
USER_ARCHETYPES = [
    {
        "id": "fresh_grad",
        "label": "Fresh Graduate (22-25 yrs, Tier 2 city)",
        "monthly_income":   35000,
        "monthly_expenses": 27000,
        "monthly_surplus":  8000,
        "savings":          12000,
        "loans": [],
        "credit_cards":     [{"limit": 50000, "outstanding": 9000, "rate_pct": 36}],
        "tax_slab_pct":     5,
        "city":             "pune",
        "tier":             "free",
        "owns_home":        False,
        "dependents":       0,
        "context": "First job, renting with flatmates, no financial plan yet.",
    },
    {
        "id": "mid_career_single",
        "label": "Mid-Career Single (28-32 yrs, metro)",
        "monthly_income":   90000,
        "monthly_expenses": 58000,
        "monthly_surplus":  32000,
        "savings":          400000,
        "loans": [
            {"loan_type": "home_loan", "remaining_balance": 3500000, "interest_rate": 8.75, "emi_amount": 32000},
        ],
        "credit_cards":     [{"limit": 300000, "outstanding": 20000, "rate_pct": 36}],
        "tax_slab_pct":     30,
        "city":             "bangalore",
        "tier":             "pro",
        "owns_home":        True,
        "dependents":       0,
        "context": "Senior engineer, just bought flat, paying home loan, 30% slab.",
    },
    {
        "id": "young_couple",
        "label": "Young Couple, Dual Income (28-34 yrs)",
        "monthly_income":   130000,
        "monthly_expenses": 80000,
        "monthly_surplus":  50000,
        "savings":          600000,
        "loans": [],
        "credit_cards":     [{"limit": 400000, "outstanding": 0, "rate_pct": 36}],
        "tax_slab_pct":     20,
        "city":             "hyderabad",
        "tier":             "pro",
        "owns_home":        False,
        "dependents":       0,
        "context": "Both working, planning to buy home in 2-3 years, no kids yet.",
    },
    {
        "id": "family_one_income",
        "label": "Single-Income Family (32-40 yrs, 2 kids)",
        "monthly_income":   65000,
        "monthly_expenses": 54000,
        "monthly_surplus":  11000,
        "savings":          90000,
        "loans": [
            {"loan_type": "personal_loan", "remaining_balance": 180000, "interest_rate": 14, "emi_amount": 5000},
        ],
        "credit_cards":     [{"limit": 100000, "outstanding": 30000, "rate_pct": 36}],
        "tax_slab_pct":     20,
        "city":             "chennai",
        "tier":             "pro",
        "owns_home":        False,
        "dependents":       2,
        "context": "Spouse not working, 2 school kids, tight surplus, worried about education costs.",
    },
    {
        "id": "high_earner",
        "label": "High Earner (34-42 yrs, debt-free)",
        "monthly_income":   220000,
        "monthly_expenses": 100000,
        "monthly_surplus":  120000,
        "savings":          2000000,
        "loans": [],
        "credit_cards":     [{"limit": 800000, "outstanding": 0, "rate_pct": 36}],
        "tax_slab_pct":     30,
        "city":             "mumbai",
        "tier":             "enterprise",
        "owns_home":        True,
        "dependents":       1,
        "context": "Director/VP level, maximising investments, optimising tax aggressively.",
    },
    {
        "id": "debt_stressed",
        "label": "Debt-Stressed Worker (26-35 yrs)",
        "monthly_income":   50000,
        "monthly_expenses": 46000,
        "monthly_surplus":  4000,
        "savings":          3000,
        "loans": [
            {"loan_type": "personal_loan", "remaining_balance": 220000, "interest_rate": 18, "emi_amount": 6500},
            {"loan_type": "credit_card",   "remaining_balance": 70000,  "interest_rate": 36, "emi_amount": 3500},
        ],
        "credit_cards":     [{"limit": 80000, "outstanding": 70000, "rate_pct": 36}],
        "tax_slab_pct":     5,
        "city":             "delhi",
        "tier":             "free",
        "owns_home":        False,
        "dependents":       1,
        "context": "Trapped in debt, CC maxed out, barely surviving, urgent restructuring needed.",
    },
    {
        "id": "freelancer_gig",
        "label": "Freelancer / Gig Worker (25-35 yrs)",
        "monthly_income":   55000,   # avg; actual varies 20k-120k
        "monthly_expenses": 38000,
        "monthly_surplus":  17000,
        "savings":          60000,
        "loans": [],
        "credit_cards":     [{"limit": 150000, "outstanding": 25000, "rate_pct": 36}],
        "tax_slab_pct":     20,
        "city":             "bangalore",
        "tier":             "pro",
        "owns_home":        False,
        "dependents":       0,
        "context": "Irregular income, no EPF, no employer insurance, responsible for own retirement.",
    },
    {
        "id": "near_retirement",
        "label": "Near Retirement (50-58 yrs)",
        "monthly_income":   160000,
        "monthly_expenses": 75000,
        "monthly_surplus":  85000,
        "savings":          6000000,
        "loans": [],
        "credit_cards":     [],
        "tax_slab_pct":     30,
        "city":             "chennai",
        "tier":             "enterprise",
        "owns_home":        True,
        "dependents":       0,
        "context": "Kids grown up, 7-10 yrs from retirement, corpus building and tax optimisation.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO TEMPLATES (14 categories, 4 query variants each)
# Each query is phrased differently to capture how real users talk about it.
# live_rates are per-category typical rates from market data.
# ─────────────────────────────────────────────────────────────────────────────
SCENARIO_TEMPLATES = [

    # 1. APPLIANCES
    {
        "category": "appliances",
        "context_note": "Evaluate outright purchase vs no-cost EMI vs personal loan. Appliances <₹50k: avoid personal loans. Check CC limit and outstanding before recommending EMI.",
        "live_rates": {"personal_loan": 13.0, "consumer_durable_loan": 0.0},
        "queries": [
            "I want to buy a Samsung 4K TV for ₹55,000. My savings are ₹40,000. Should I use savings or take a no-cost EMI?",
            "My refrigerator broke down. A new double-door fridge costs ₹42,000. I don't want to touch my emergency fund. What's the best way to buy it?",
            "Planning to buy a 1.5-ton split AC before summer. Price is ₹48,000. Should I buy outright, use my credit card EMI, or wait 2 months and save?",
            "I want to buy a front-load washing machine for ₹35,000. I have ₹20,000 saved. Is a consumer durable loan a good idea?",
        ],
    },

    # 2. GADGETS
    {
        "category": "gadgets",
        "context_note": "Gadgets depreciate fast. No-cost EMI with 0 processing fee beats personal loans. Check if it is a work necessity (laptop) vs want (gaming PC). Warn against CC rollover.",
        "live_rates": {"personal_loan": 13.0},
        "queries": [
            "I want to buy an iPhone 16 Pro for ₹1.35 lakhs. I have ₹50,000 saved. Is 12-month no-cost EMI on my credit card smart?",
            "I need a MacBook Pro for my freelance design work. It costs ₹1.8 lakhs. I have ₹60,000 saved and decent monthly surplus. What's the best way to finance it?",
            "I want to upgrade my DSLR camera for photography side income. The camera costs ₹95,000. How should I plan this purchase?",
            "I'm buying a gaming PC for ₹1.2 lakhs. I have no immediate use case for it professionally. Should I wait and save or take an EMI?",
        ],
    },

    # 3. VEHICLE
    {
        "category": "vehicle",
        "context_note": "Apply 40% EMI rule on monthly surplus. Include insurance year 1 and maintenance. For EVs flag FAME II subsidy eligibility. Show 30% down payment scenario.",
        "live_rates": {"auto_loan_rate_pct_pa": 8.75, "car_loan": 8.75},
        "queries": [
            "I want to buy a Maruti Swift VXI in Bangalore. On-road price is around ₹8.5 lakhs. My monthly surplus is limited. What are my best financing options?",
            "Planning to buy an Ola Electric S1 Pro EV scooter for ₹1.4 lakhs. Is there any FAME II or state subsidy I can claim? Best way to finance?",
            "I need a reliable second-hand car. Found a 3-year-old Honda City for ₹6 lakhs. Should I take a used car loan or use my savings plus partial loan?",
            "I want to buy a Royal Enfield Meteor 350 for ₹2.2 lakhs. I have ₹80,000 saved. Should I take a two-wheeler loan or just save for 6 more months?",
        ],
    },

    # 4. SHORT TRIP
    {
        "category": "short_trip",
        "context_note": "Short trips are pure savings goals. Check if achievable from surplus in the timeline. Never recommend a loan for travel. Suggest travel credit card rewards only if CC is fully paid.",
        "live_rates": {},
        "queries": [
            "Planning a 4-day Goa trip with friends next month. My share will be about ₹25,000 including flights, hotel, and activities. How do I fund this without going into debt?",
            "Want to do a family road trip to Coorg in 6 weeks. Estimated total cost is ₹32,000 including fuel, stay, and food. How do I save for this alongside regular expenses?",
            "I'm planning a solo trek to Leh-Ladakh in 3 months. Total budget is ₹45,000. What's the most efficient way to set aside this money?",
            "Friends are planning a Rajasthan trip in 2 months. My share is ₹18,000. I can save ₹8,000 per month. Can I do this without a loan?",
        ],
    },

    # 5. LONG VACATION
    {
        "category": "long_vacation",
        "context_note": "Long-horizon travel: recommend SIP in liquid fund or RD to build corpus. Calculate required monthly saving. Warn about forex risk for international trips. Factor in leave encashment.",
        "live_rates": {},
        "queries": [
            "I want to take my family on a Europe trip in 18 months. Estimated total cost is ₹4.5 lakhs including flights, hotels, and visa. How do I build this corpus systematically?",
            "Dream of visiting Japan next year for 2 weeks. Solo budget is ₹3 lakhs including international flights. Should I do a recurring deposit or a liquid fund SIP?",
            "Planning a Southeast Asia vacation — Thailand, Vietnam, Bali — in 12 months. Budget is ₹2 lakhs for 2 people. Best way to save and grow this money?",
            "Want to take a 10-day Maldives honeymoon trip in 8 months. Budget is ₹2.5 lakhs. I have ₹80,000 saved. How do I reach this goal?",
        ],
    },

    # 6. MEDICAL / HEALTH
    {
        "category": "medical",
        "context_note": "Emergency fund = 6x monthly expenses in liquid fund or sweep FD. Health insurance floater ₹5-10L costs ~₹12-18k/year. Surgery cost: evaluate loan vs liquidation vs insurance claim.",
        "live_rates": {"personal_loan": 13.0},
        "queries": [
            "I had a sudden medical emergency costing ₹85,000 and wiped out my savings. How do I rebuild my emergency fund and ensure this doesn't happen again?",
            "My mother needs a knee replacement surgery that costs ₹2.8 lakhs. I have ₹1 lakh saved. How do I arrange the balance quickly without a high-interest loan?",
            "I want to build a medical emergency corpus of ₹3 lakhs over the next 2 years alongside my regular expenses. What is the best approach?",
            "I don't have health insurance. I'm 28, single, fairly healthy. Is buying a ₹10L family floater now worth it, and how does it fit in my budget?",
        ],
    },

    # 7. TAX SAVING
    {
        "category": "tax_saving",
        "context_note": "Compare old vs new regime based on income and deductions. 80C: ELSS (best returns, 3yr lock), PPF (safe, 15yr), NPS (extra 50k under 80CCD1B). Show post-tax effective return.",
        "live_rates": {},
        "queries": [
            "I'm in the 30% tax slab with income of ₹18 LPA. I haven't made any 80C investments this year. I have ₹1.5 lakhs to invest before March 31. Which option gives the best post-tax return?",
            "Should I choose the old tax regime or the new regime? I have a home loan, ₹1.5L in 80C investments, and my gross income is ₹14 LPA.",
            "I want to reduce my tax outgo. I'm in the 20% slab. What is the right mix of ELSS, PPF, and NPS contributions to maximise savings?",
            "I just started a new job at ₹12 LPA. HR is asking me to declare investments. I have no existing commitments. Which regime and which instruments should I choose?",
        ],
    },

    # 8. HOME BUYING
    {
        "category": "home_buying",
        "context_note": "Rent vs buy breakeven = 5-8 years in Indian metros. EMI should not exceed 40% of take-home. Down payment: 20% minimum. Check CIBIL score 750+ for best rates. Tax benefit: 80C principal 1.5L + 24b interest 2L.",
        "live_rates": {"home_loan": 8.5, "auto_loan_rate_pct_pa": 8.75},
        "queries": [
            "I'm paying ₹28,000 rent in Bangalore and considering buying a 2BHK flat for ₹85 lakhs. Should I buy now with a home loan or keep renting and invest the difference?",
            "I want to buy my first home in Hyderabad. The flat costs ₹60 lakhs. I have ₹8 lakhs saved for down payment. How much more do I need and how long will it take to get there?",
            "I have a home loan of ₹45 lakhs at 8.75%. My mutual fund SIP is returning 12% CAGR. Should I prepay the home loan or continue the SIP?",
            "My CIBIL score is 680. I want to take a home loan in 18 months. What steps should I take to improve my score and qualify for the best rate?",
        ],
    },

    # 9. EDUCATION
    {
        "category": "education",
        "context_note": "Child education: use Sukanya (girl child), Equity mutual fund, education insurance. Own MBA: ROI analysis, education loan at 10-11%. Upskilling: short-term, ROI in 6-12 months.",
        "live_rates": {"personal_loan": 13.0, "education_loan": 10.5},
        "queries": [
            "My daughter is 3 years old. I want to build a ₹30 lakh corpus for her higher education over the next 15 years. What is the best investment approach?",
            "I want to do a part-time MBA from a good institute. It costs ₹8 lakhs over 2 years. I have ₹2 lakhs saved. Should I take an education loan or fund it myself?",
            "I want to upskill in data science. A good online programme costs ₹80,000. I expect a 30% salary hike after 6 months. How do I fund this without disrupting savings?",
            "My son is 10 years old. I want to fund his IIT/IIM dream — roughly ₹15-20 lakhs over 7-8 years. How should I invest to get there?",
        ],
    },

    # 10. WEDDING
    {
        "category": "wedding",
        "context_note": "Own wedding: target savings 12-18 months before. Kids wedding: 20-year SIP. Warn against personal loan for wedding — high interest on a non-asset. Gold as partial hedge for jewellery costs.",
        "live_rates": {"personal_loan": 13.0},
        "queries": [
            "I'm getting married in 18 months. Total wedding budget is ₹8 lakhs. I have ₹2 lakhs saved. How do I build the rest without taking a personal loan?",
            "My parents want to spend ₹15 lakhs on my sister's wedding in 2 years. They have ₹5 lakhs saved. How should they invest the rest and manage the shortfall?",
            "My daughter is 5 years old. I want to build a ₹20 lakh corpus for her wedding in 20 years. What SIP amount do I need to start today?",
            "I need ₹4 lakhs for wedding expenses in 6 months. I have ₹1.5 lakhs saved. Should I take a personal loan for the rest or liquidate my mutual funds?",
        ],
    },

    # 11. RETIREMENT
    {
        "category": "retirement",
        "context_note": "Retirement corpus = 25x annual expenses (4% rule). NPS: 80CCD1B extra 50k, lower fees, illiquid. EPF: 8.25% guaranteed, employer match. SIP: higher returns, flexible. Balance all three.",
        "live_rates": {},
        "queries": [
            "I'm 28 and want to retire by 50. My current monthly expense is ₹50,000. How much corpus do I need and how much should I invest per month starting now?",
            "I have EPF at work. Should I also invest in NPS? Or is a SIP in mutual funds better for retirement? I'm 35 now.",
            "I'm 52, have ₹60 lakhs saved, and want to retire in 8 years. My monthly expenses are ₹75,000. Do I have enough and what should I do with my savings now?",
            "I want to do early retirement at 45. I'm 30 now with ₹5 lakhs saved and ₹40,000 monthly surplus. What is the roadmap to FIRE?",
        ],
    },

    # 12. CREDIT REPAIR
    {
        "category": "credit_repair",
        "context_note": "CIBIL <700: identify derogatory accounts, pay overdue first, reduce credit utilisation below 30%, avoid new applications. 6-12 months of discipline = 50-100 point improvement.",
        "live_rates": {"personal_loan": 18.0},
        "queries": [
            "My CIBIL score is 620 because I missed a few EMI payments last year. I'm now paying on time. How long will it take to recover and what should I do to speed it up?",
            "I have ₹1.2 lakhs outstanding on my credit card at 36% interest and I'm only paying the minimum. I also have a personal loan at 18%. What's the fastest way out of this debt trap?",
            "I have 4 credit cards and my total utilisation is 82%. My CIBIL score has dropped to 650. Should I close some cards or just pay them down?",
            "I defaulted on a personal loan 2 years ago and settled it for less than the full amount. My CIBIL score is 580. How do I rebuild my credit profile?",
        ],
    },

    # 13. SALARY PLANNING
    {
        "category": "salary_planning",
        "context_note": "New salary: allocate before spending (50-30-20 rule or Indian variant). Hike: redirect to goals not lifestyle inflation. First job: build emergency fund first, then invest.",
        "live_rates": {},
        "queries": [
            "I just got my first salary of ₹42,000 per month. I don't know how to allocate it. What should be my priority — emergency fund, investments, or clearing credit card dues?",
            "I got a 40% hike and my salary is now ₹1.2 lakhs per month. I don't want to inflate my lifestyle. How should I allocate the additional ₹35,000 per month?",
            "I'm a fresher earning ₹35,000 in hand. After rent, food, and travel I'm left with ₹8,000. How do I make meaningful progress financially with such a small surplus?",
            "I get both CTC and in-hand confused. My CTC is ₹10 LPA but my in-hand is ₹64,000. How do I plan my finances based on what I actually take home?",
        ],
    },

    # 14. SIDE INCOME
    {
        "category": "side_income",
        "context_note": "Side income: taxable as 'income from other sources' or business income. Freelancers: advance tax quarterly if projected tax > 10k. Rental: 30% standard deduction on rent. Stock trading: STCG 15%, LTCG 10% above 1L.",
        "live_rates": {},
        "queries": [
            "I have a flat I'm renting out for ₹18,000 per month. How much tax do I owe on this rental income and how do I reduce it legally?",
            "I do freelance projects on the side and earned ₹3.5 lakhs this year on top of my salary. How should I declare this and save tax on it?",
            "I made ₹85,000 profit from stock trading this year — mix of short-term and long-term gains. How is this taxed and should I offset any losses?",
            "I want to start a side business selling handmade products online. Expecting ₹20,000-₹30,000 per month revenue. How do I structure this financially and tax-efficiently?",
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# ADVISORY BANK — category-specific financial rules injected into responses
# ─────────────────────────────────────────────────────────────────────────────
ADVISORIES = {
    "appliances":    "Rule: appliances <₹50k → pay from savings or 0% EMI only. Never a personal loan for a depreciating asset unless truly urgent. Check if the CC 0-cost EMI has a processing fee hidden in T&Cs.",
    "gadgets":       "Gadgets depreciate 30-40% in year 1. If it's a work tool (laptop, camera), it's an investment with ROI. If it's lifestyle (gaming), wait and save. No-cost EMI beats personal loan only if you pay the full CC bill on time.",
    "vehicle":       "EMI ≤ 40% of monthly surplus. On-road = ex-showroom + RTO (8-11%) + insurance (2.5%) + accessories. Include ₹8,000-12,000/year maintenance in year-2+ budget. Check FAME II subsidy for EVs before quoting price.",
    "short_trip":    "Travel is a liability, not an asset. Fund 100% from savings. Never take a loan for a vacation under any circumstances. Travel credit card reward points offset 5-8% of costs if you pay in full every month.",
    "long_vacation": "Start a dedicated travel RD or liquid fund immediately. Required monthly saving = (target - current savings) / months. Add 15% buffer for forex fluctuation on international trips.",
    "medical":       "Emergency fund = 6× monthly expenses in a sweep FD or liquid fund — accessible same day. A ₹10L family floater health insurance costs ₹12,000-18,000/year and can save lakhs. Get it before a health event, not after.",
    "tax_saving":    "ELSS: best post-tax returns, 3-yr lock, market risk. PPF: guaranteed 7.1%, 15-yr lock, fully tax-free at maturity — best for conservative. NPS: extra ₹50k under 80CCD(1B) beyond 80C limit. Mix all three based on risk appetite.",
    "home_buying":   "Rent vs buy: buy wins after 5-7 years of staying in the same city. CIBIL ≥ 750 → best rates (8.35-8.5%). 20% down payment minimum. Tax benefit: ₹1.5L principal (80C) + ₹2L interest (24b) per year in old regime.",
    "education":     "Child education: equity mutual fund SIP for 10+ yr horizon beats all alternatives at 12% CAGR. Education loan interest: full deduction under 80E for 8 years. For own MBA, calculate ROI = salary hike / total cost — break-even usually 2-3 years.",
    "wedding":       "Personal loan for wedding = paying 13-18% interest on an expense with zero ROI. Save 12-18 months in advance. Gold ETF or Sovereign Gold Bond for jewellery corpus — avoids making charges and theft risk.",
    "retirement":    "Corpus needed = 25× annual expenses (4% safe withdrawal rate). EPF + NPS + SIP is the ideal trinity. NPS: annuity at 60 provides lifetime pension. FIRE at 45 needs ~33× annual expenses (3% withdrawal for longer horizon).",
    "credit_repair": "Credit utilisation < 30% on every card individually. Never miss a payment — even minimum. Each settled/defaulted account stays on CIBIL for 7 years. Score recovery: 6-12 months disciplined payments = +50-100 points.",
    "salary_planning": "50-30-20 rule: 50% needs, 30% wants, 20% savings+investments. For first salary: build 3-month emergency fund first. Hike windfall: redirect 80% to goals, allow 20% lifestyle upgrade to stay motivated.",
    "side_income":   "Rental: 30% standard deduction, then taxed at slab. Freelance: presumptive tax under 44ADA at 50% of gross receipts if <₹50L/year — massively reduces tax. LTCG on equity: 10% above ₹1L exemption. STCG: 15% flat.",
}


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE GENERATOR — financially grounded, not canned
# ─────────────────────────────────────────────────────────────────────────────
def generate_response(query, user, goal, ranked, techniques, category):
    surplus   = user["monthly_surplus"]
    income    = user["monthly_income"]
    savings   = user["savings"]
    label     = user["label"]
    loans     = user["loans"]
    best      = ranked.get("best") or {}
    all_strats = ranked.get("ranked") or []

    lines = []

    # Technique opening
    openers = {
        "first_principles":  f"Let me strip this back: what are you actually trying to achieve? Not just '{category}' but the right outcome for your ₹{surplus:,}/month surplus.",
        "second_order":      f"Before we commit: what changes in your monthly cash-flow AFTER this decision? Let's think two moves ahead.",
        "inversion":         f"What would make this goal impossible? Let's identify the blockers first, then remove them one by one.",
        "constraint_relax":  f"The stated constraint might not be the real constraint. Let's relax one assumption and see what opens up.",
        "reframing":         f"You're asking about '{category}' — let me reframe: what is the cheapest total cost of achieving the actual outcome you want?",
        "analogical":        f"Think of this like load balancing — spread the cost across time nodes to eliminate the single point of financial stress.",
    }
    for t in techniques[:1]:
        if t in openers:
            lines.append(openers[t])

    # User snapshot
    lines.append(f"\n**Your financial position ({label}):**")
    lines.append(f"- Monthly income: ₹{income:,}  |  Surplus: ₹{surplus:,}  |  Savings: ₹{savings:,}")
    if loans:
        for l in loans:
            lines.append(f"- Loan: {l['loan_type']} ₹{l['remaining_balance']:,} @ {l['interest_rate']}% (EMI ₹{l.get('emi_amount',0):,})")
    if user.get("owns_home"):
        lines.append(f"- Owns home: yes")
    if user.get("dependents", 0) > 0:
        lines.append(f"- Dependents: {user['dependents']}")

    # Goal
    if goal:
        lines.append(f"\n**Goal: {goal.goal_type.value.replace('_',' ').title()}**")
        if goal.target_amount:
            lines.append(f"- Target: ₹{goal.target_amount:,.0f}")
        if goal.timeline_months:
            monthly_needed = (goal.target_amount or 0) / goal.timeline_months if goal.timeline_months else 0
            lines.append(f"- Timeline: {goal.timeline_months} months  (requires ~₹{monthly_needed:,.0f}/month saving)")
            feasibility = "feasible" if monthly_needed <= surplus * 0.6 else "aggressive — needs adjustment"
            lines.append(f"- Feasibility check: {feasibility}")

    # Strategies
    if all_strats:
        lines.append(f"\n**{len(all_strats)} strategies evaluated:**")
        for s in all_strats[:3]:
            tag = f" [{s.get('recommendation_tag')}]" if s.get("recommendation_tag") else ""
            feas = "✓" if s.get("feasible") else "⚠ stretches budget"
            lines.append(f"\n**{s.get('rank','')}. {s['name']}**{tag} {feas}")
            lines.append(f"   {s.get('description','')}")
            outflow = s.get('monthly_outflow', 0)
            total = s.get('total_cost', 0)
            interest = s.get('interest_paid', 0)
            pct = round(outflow / surplus * 100) if surplus else 0
            lines.append(f"   Monthly: ₹{outflow:,} ({pct}% of surplus)  |  Total: ₹{total:,}  |  Interest: ₹{interest:,}  |  Risk: {s.get('risk_level','?')}")
            for n in (s.get("notes") or [])[:2]:
                lines.append(f"   → {n}")

    # Recommendation
    if best:
        lines.append(f"\n**Recommendation: {best['name']}**")
        mo = best.get("monthly_outflow", 0)
        tc = best.get("total_cost", 0)
        ip = best.get("interest_paid", 0)
        ts = best.get("tax_saving", 0)
        pct = round(mo / surplus * 100) if surplus else 0
        lines.append(f"Uses ₹{mo:,}/month ({pct}% of surplus). Total outflow: ₹{tc:,}. Interest cost: ₹{ip:,}.")
        if ts > 0:
            lines.append(f"Annual tax saving: ₹{ts:,} (old regime, {user.get('tax_slab_pct',20)}% slab).")

    # Near-tie flag
    if ranked.get("near_tie") and len(all_strats) >= 2:
        s2 = all_strats[1]
        lines.append(
            f"\n⚠️ Near tie: '{best.get('name','')}' vs '{s2['name']}' "
            f"(scores {best.get('composite_score',0):.2f} vs {s2.get('composite_score',0):.2f}). "
            f"Choose based on your risk preference."
        )

    # Advisory
    adv = ADVISORIES.get(category, "")
    if adv:
        lines.append(f"\n**Advisory:** {adv}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# TRAINER LOOP
# ─────────────────────────────────────────────────────────────────────────────
def run_training(verbose=True):
    stats = {
        "total": 0, "winners": 0, "stored": 0, "errors": 0,
        "by_category": {}, "by_archetype": {}, "scores": [],
    }

    load_seed_traces()

    for scenario in SCENARIO_TEMPLATES:
        cat = scenario["category"]
        stats["by_category"][cat] = {"runs": 0, "winners": 0, "errors": 0}

        for user in USER_ARCHETYPES:
            uid = user["id"]
            if uid not in stats["by_archetype"]:
                stats["by_archetype"][uid] = {"runs": 0, "winners": 0}

            # Rotate query variants across archetypes
            aidx  = USER_ARCHETYPES.index(user)
            query = scenario["queries"][aidx % len(scenario["queries"])]

            stats["total"] += 1
            stats["by_category"][cat]["runs"] += 1
            stats["by_archetype"][uid]["runs"] += 1

            if verbose:
                print(f"  [{cat.upper():<16} × {uid:<22}] ", end="", flush=True)

            profile = {
                "monthly_income":   user["monthly_income"],
                "monthly_surplus":  user["monthly_surplus"],
                "monthly_expenses": user["monthly_expenses"],
                "savings":          user["savings"],
                "city":             user["city"],
                "tier":             user["tier"],
                "tax_slab_pct":     user["tax_slab_pct"],
                "owns_home":        user.get("owns_home", False),
                "dependents":       user.get("dependents", 0),
            }

            try:
                goal      = decompose_goal(query, profile)
                strats    = compute_strategies(goal, profile,
                               live_rates=scenario.get("live_rates", {}),
                               loans=user.get("loans", []))
                ranked    = rank_strategies(strats, profile)
                techniques = tag_techniques(query, {"goal_type": goal.goal_type.value})
                response  = generate_response(query, user, goal, ranked, techniques, cat)

                ev = evaluate(
                    query=query,
                    response_text=response,
                    goal_type=goal.goal_type.value,
                    audit_warnings=[],
                    compliance_result={"passed": True, "flags": []},
                    user_feedback=None,
                )

                stats["scores"].append(ev.score)

                best_name = (ranked.get("best") or {}).get("name", "N/A")[:30]
                if verbose:
                    print(f"goal={goal.goal_type.value:<12} strats={len(strats)} score={ev.score:.3f} winner={ev.is_winner} techs={techniques}")

                if ev.is_winner:
                    stats["winners"] += 1
                    stats["by_category"][cat]["winners"] += 1
                    stats["by_archetype"][uid]["winners"] += 1

                    ok = store_save(
                        query=query,
                        goal_struct={
                            "goal_type":      goal.goal_type.value,
                            "target_amount":  goal.target_amount,
                            "timeline_months": goal.timeline_months,
                        },
                        strategies=strats[:3],
                        ranked_output=ranked,
                        response_text=response[:600],
                        eval_result=ev,
                        user_id=abs(hash(uid)) % 100000,
                    )
                    if ok:
                        stats["stored"] += 1

            except Exception as e:
                stats["errors"] += 1
                stats["by_category"][cat]["errors"] = stats["by_category"][cat].get("errors", 0) + 1
                if verbose:
                    print(f"ERROR: {e}")
                continue

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    total_runs = len(SCENARIO_TEMPLATES) * len(USER_ARCHETYPES)
    print("=" * 80)
    print("TORA SCENARIO TRAINER v2")
    print(f"Categories: {len(SCENARIO_TEMPLATES)}  |  Archetypes: {len(USER_ARCHETYPES)}  |  Total runs: {total_runs}")
    print("=" * 80)

    t0 = time.time()
    stats = run_training(verbose=True)
    elapsed = time.time() - t0

    scores = stats["scores"]
    print()
    print("=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)
    print(f"  Total runs:       {stats['total']}")
    print(f"  Winners (≥0.75):  {stats['winners']}")
    print(f"  Stored traces:    {stats['stored']}")
    print(f"  Errors:           {stats['errors']}")
    if scores:
        print(f"  Avg score:        {sum(scores)/len(scores):.3f}")
        print(f"  Min / Max score:  {min(scores):.3f} / {max(scores):.3f}")
    print(f"  Time:             {elapsed:.1f}s")

    print()
    print(f"  {'Category':<18} {'Runs':>5} {'Winners':>8} {'Errors':>7} {'Win%':>6}")
    print(f"  {'-'*18} {'-'*5} {'-'*8} {'-'*7} {'-'*6}")
    for cat, v in stats["by_category"].items():
        wp = v['winners']/v['runs']*100 if v['runs'] else 0
        print(f"  {cat:<18} {v['runs']:>5} {v['winners']:>8} {v.get('errors',0):>7} {wp:>5.0f}%")

    print()
    print(f"  {'Archetype':<24} {'Runs':>5} {'Winners':>8} {'Win%':>6}")
    print(f"  {'-'*24} {'-'*5} {'-'*8} {'-'*6}")
    for uid, v in stats["by_archetype"].items():
        wp = v['winners']/v['runs']*100 if v['runs'] else 0
        print(f"  {uid:<24} {v['runs']:>5} {v['winners']:>8} {wp:>5.0f}%")

    print()
    print("  Hot index after training:")
    for gt, count in sorted(get_index_stats().items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"  {gt:<16} {count:>3}  {bar}")

    summary = {
        "total": stats["total"],
        "winners": stats["winners"],
        "stored": stats["stored"],
        "errors": stats["errors"],
        "avg_score": round(sum(scores)/len(scores), 3) if scores else 0,
        "min_score": round(min(scores), 3) if scores else 0,
        "max_score": round(max(scores), 3) if scores else 0,
        "by_category": stats["by_category"],
        "by_archetype": stats["by_archetype"],
        "hot_index": get_index_stats(),
    }
    out = os.path.join(os.path.dirname(__file__), "training_summary.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary → {out}")


if __name__ == "__main__":
    main()
