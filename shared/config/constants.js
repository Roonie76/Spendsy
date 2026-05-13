import * as LucideIcons from "lucide-react";

/**
 * --- HELPER TO DETECT ENVIRONMENT ---
 * Optimized for Vite & gateway-based microservices.
 * Fetches variables from .env (VITE_ prefix required).
 */
const viteEnv =
  typeof import.meta !== "undefined" && import.meta.env ? import.meta.env : {};

const getEnv = (key) => {
  // Vite static replacement (must be written out)
  const viteEnvs = {
    APP_VERSION: viteEnv.VITE_APP_VERSION,
    API_BASE_URL: viteEnv.VITE_API_BASE_URL,
    GATEWAY_URL: viteEnv.VITE_GATEWAY_URL,
    FINANCE_URL: viteEnv.VITE_FINANCE_URL,
    AUTH_URL: viteEnv.VITE_AUTH_URL,
    AI_URL: viteEnv.VITE_AI_URL,
    LEGACY_API_URL: viteEnv.VITE_API_URL,
  };

  if (viteEnvs[key]) return viteEnvs[key];

  // Mobile/Node fallback
  if (typeof process !== "undefined" && process.env) {
    return process.env[`EXPO_PUBLIC_${key}`] || process.env[key];
  }

  return undefined;
};

// --- METADATA & API CONFIG ---
export const CURRENCY_SYMBOL = "₹";
export const APP_VERSION = getEnv("APP_VERSION") || "1.0.0";
const legacyApiUrl = viteEnv.VITE_API_URL || getEnv("API_BASE_URL");
export const GATEWAY_URL =
  getEnv("GATEWAY_URL") || viteEnv.VITE_GATEWAY_URL || "http://localhost:8080";

export const API_BASE_URL =
  getEnv("FINANCE_URL") ||
  viteEnv.VITE_FINANCE_URL ||
  (legacyApiUrl && legacyApiUrl.includes("/finance") ? legacyApiUrl : `${GATEWAY_URL}/finance`);

export const AUTH_BASE_URL =
  getEnv("AUTH_URL") || viteEnv.VITE_AUTH_URL || `${GATEWAY_URL}/auth`;

export const AI_BASE_URL =
  getEnv("LEGACY_AI_URL") || viteEnv.VITE_LEGACY_AI_URL || `${GATEWAY_URL}/ai_legacy`;

export const TORA_BASE_URL =
  getEnv("AI_URL") || viteEnv.VITE_AI_URL || `${GATEWAY_URL}/tora`;

// --- DOMAIN CONSTANTS ---
const {
  Briefcase,
  TrendingUp,
  Home: HomeIcon,
  Zap,
  Coffee,
  ShoppingBag,
  Car,
  Gift,
  Smartphone,
  Activity,
  Heart,
  GraduationCap,
} = LucideIcons;

export const CATEGORIES = [
  {
    id: "salary",
    name: "Salary",
    icon: Briefcase,
    color: "bg-emerald-500/20 text-emerald-300",
    keywords: [
      "payroll",
      "salary",
      "deposit",
      "transfer",
      "neft",
      "imps",
      "credit interest",
    ],
  },
  {
    id: "investment",
    name: "Invest",
    icon: TrendingUp,
    color: "bg-teal-500/20 text-teal-300",
    keywords: [
      "zerodha",
      "groww",
      "upstox",
      "vanguard",
      "fidelity",
      "crypto",
      "coinbase",
      "stock",
      "sip",
      "mutual",
      "ppf",
      "nps",
      "elss",
      "redeem",
    ],
  },
  {
    id: "housing",
    name: "Housing",
    icon: HomeIcon,
    color: "bg-indigo-500/20 text-indigo-300",
    keywords: [
      "rent",
      "mortgage",
      "repair",
      "home",
      "depot",
      "furniture",
      "urban company",
    ],
  },
  {
    id: "utilities",
    name: "Utilities",
    icon: Zap,
    color: "bg-yellow-500/20 text-yellow-300",
    keywords: [
      "bill",
      "electricity",
      "mobile",
      "internet",
      "broadband",
      "insurance",
      "premium",
      "lic",
    ],
  },
  {
    id: "food",
    name: "Food",
    icon: Coffee,
    color: "bg-orange-500/20 text-orange-300",
    keywords: [
      "cafe",
      "coffee",
      "restaurant",
      "mcdonalds",
      "burger",
      "pizza",
      "starbucks",
      "grocery",
      "market",
      "food",
      "zomato",
      "swiggy",
      "choco",
    ],
  },
  {
    id: "shopping",
    name: "Shopping",
    icon: ShoppingBag,
    color: "bg-sky-500/20 text-sky-300",
    keywords: [
      "amazon",
      "flipkart",
      "myntra",
      "store",
      "mall",
      "clothing",
      "shoe",
      "nike",
      "zara",
      "shop",
      "decathlon",
      "ajio",
    ],
  },
  {
    id: "transport",
    name: "Transport",
    icon: Car,
    color: "bg-blue-500/20 text-blue-300",
    keywords: [
      "uber",
      "ola",
      "rapido",
      "lyft",
      "taxi",
      "gas",
      "fuel",
      "shell",
      "parking",
      "train",
      "bus",
      "metro",
      "petrol",
      "hpcl",
      "bpcl",
      "irctc",
    ],
  },
  {
    id: "entertainment",
    name: "Fun",
    icon: Gift,
    color: "bg-pink-500/20 text-pink-300",
    keywords: [
      "netflix",
      "spotify",
      "cinema",
      "movie",
      "game",
      "steam",
      "playstation",
      "ticket",
      "bookmyshow",
      "pvr",
      "inox",
      "hotstar",
    ],
  },
  {
    id: "tech",
    name: "Tech",
    icon: Smartphone,
    color: "bg-cyan-500/20 text-cyan-300",
    keywords: [
      "apple",
      "google",
      "software",
      "hardware",
      "electronics",
      "croma",
      "reliance digital",
    ],
  },
  {
    id: "health",
    name: "Health",
    icon: Heart,
    color: "bg-red-500/20 text-red-300",
    keywords: ["doctor", "hospital", "medicine", "pharmacy", "clinic", "dental"],
  },
  {
    id: "education",
    name: "Education",
    icon: GraduationCap,
    color: "bg-violet-500/20 text-violet-300",
    keywords: ["school", "college", "tuition", "course", "udemy", "book", "exam"],
  },
  {
    id: "other",
    name: "Other",
    icon: Activity,
    color: "bg-slate-500/20 text-slate-300",
    keywords: [],
  },
];

export const TABS = {
  HOME: "home",
  HISTORY: "history",
  ADD: "add",
  AUDIT: "audit",
  STATS: "stats",
  WEALTH: "wealth",
  PROFILE: "profile",

  DEBIT_CARDS: "debit_cards",
  CREDIT_CARDS: "credit_cards",
  SETTINGS: "settings",
  BANK_ACCOUNTS: "bank_accounts",
  GOALS: "goals",
  PLANNER: "planner",
  BUDGET: "budget",
  LOANS: "loans",
  CHAT: "chat",
  ITR_FILING: "itr_filing",
};

export const BANKS = [
  "SBI",
  "HDFC Bank",
  "ICICI Bank",
  "Axis Bank",
  "Kotak Mahindra Bank",
  "IndusInd Bank",
  "Bank of Baroda",
  "Punjab National Bank",
  "Union Bank of India",
  "Canara Bank",
  "IDFC First Bank",
  "Yes Bank",
  "Federal Bank",
  "Standard Chartered",
  "Citi Bank",
  "HSBC",
  "DBS Bank",
  "Bandhan Bank",
  "South Indian Bank",
  "Karnataka Bank",
];

export const UNITS = [
  { label: "₹", value: 1 },
  { label: "K", value: 1000 },
  { label: "L", value: 100000 },
  { label: "Cr", value: 10000000 },
];

export const TAX_CONSTANTS = {
  // ── FY 2025-26 New Regime (Union Budget 2025) ────────────────────────────
  NEW_REGIME: {
    SLABS: [
      { limit: 400000,  rate: 0.00 },
      { limit: 800000,  rate: 0.05 },
      { limit: 1200000, rate: 0.10 },
      { limit: 1600000, rate: 0.15 },
      { limit: 2000000, rate: 0.20 },
      { limit: 2400000, rate: 0.25 },
      { limit: null,    rate: 0.30 },
    ],
    REBATE_LIMIT: 1200000,   // ₹12L — full tax rebate u/s 87A
    REBATE_MAX: 60000,       // Max rebate amount
    STANDARD_DEDUCTION: 75000,
    CESS: 0.04,
    MAX_SURCHARGE_RATE: 0.25,  // Surcharge capped at 25% in new regime
  },

  // ── Old Regime (unchanged) ───────────────────────────────────────────────
  OLD_REGIME: {
    SLABS: [
      { limit: 250000,  rate: 0.00 },
      { limit: 500000,  rate: 0.05 },
      { limit: 1000000, rate: 0.20 },
      { limit: null,    rate: 0.30 },
    ],
    SLABS_SENIOR: [
      { limit: 300000,  rate: 0.00 },
      { limit: 500000,  rate: 0.05 },
      { limit: 1000000, rate: 0.20 },
      { limit: null,    rate: 0.30 },
    ],
    SLABS_SUPER_SENIOR: [
      { limit: 500000,  rate: 0.00 },
      { limit: 1000000, rate: 0.20 },
      { limit: null,    rate: 0.30 },
    ],
    REBATE_LIMIT: 500000,
    REBATE_MAX: 12500,
    STANDARD_DEDUCTION: 75000,  // Raised to ₹75K from FY24-25 onwards
    CESS: 0.04,
    MAX_SURCHARGE_RATE: 0.37,
  },

  // ── Surcharge tiers ──────────────────────────────────────────────────────
  SURCHARGE: [
    { threshold: 5000000,  rate: 0.10 },
    { threshold: 10000000, rate: 0.15 },
    { threshold: 20000000, rate: 0.25 },
    { threshold: 50000000, rate: 0.37 },  // 0.25 in new regime (capped above)
  ],

  // ── Deduction limits (Chapter VI-A, FY 2025-26) ──────────────────────────
  LIMITS: {
    // 80C aggregate
    SECTION_80C: 150000,

    // 80D — health insurance
    SECTION_80D_SELF: 25000,
    SECTION_80D_SELF_SENIOR: 50000,
    SECTION_80D_PARENTS: 50000,         // ₹25K if non-senior, ₹50K if senior
    SECTION_80D_PARENTS_SENIOR: 100000, // both parents senior
    SECTION_80D_PREVENTIVE: 5000,       // sub-limit, no bills needed

    // 80DD — disabled dependent
    SECTION_80DD: 75000,
    SECTION_80DD_SEVERE: 125000,

    // 80DDB — specified diseases
    SECTION_80DDB: 40000,
    SECTION_80DDB_SENIOR: 100000,

    // 80E — education loan (no upper limit)
    SECTION_80E: null,

    // 80EEA — affordable housing loan interest
    SECTION_80EEA: 150000,

    // 80EEB — EV loan interest
    SECTION_80EEB: 150000,

    // 80G — donations (split by bucket)
    SECTION_80G_100_PCT: 1.00,  // multiplier on donation amount
    SECTION_80G_50_PCT: 0.50,
    SECTION_80G_CAPPED_GTI: 0.10, // max 10% of Adjusted GTI

    // 80GG — rent if no HRA
    SECTION_80GG_ANNUAL: 60000,   // ₹5K/month × 12
    SECTION_80GG_MONTHLY: 5000,

    // 80GGA — scientific research donations
    SECTION_80GGA: null,

    // 80GGC — political party donations
    SECTION_80GGC: null,

    // 80NPS
    SEC_80CCD_1B: 50000,          // NPS self — over and above 80C

    // 80TTA / 80TTB
    SECTION_80TTA: 10000,
    SECTION_80TTB_SENIOR: 50000,

    // 80U — self disability
    SECTION_80U: 75000,
    SECTION_80U_SEVERE: 125000,

    // House property / home loans
    SECTION_24B_SOP: 200000,     // Self-occupied — ₹2L cap
    SECTION_80EE: 50000,          // First-home buyers (older loans)

    // Presumptive taxation
    PRESUMPTIVE_44ADA: 0.50,              // 50% of gross receipts
    PRESUMPTIVE_TURNOVER_LIMIT: 30000000, // ₹3 Cr for 44AD with digital receipts
    PRESUMPTIVE_44AD_RATE: 0.08,          // 8% of turnover (6% for digital)
    PRESUMPTIVE_44AE_PER_VEHICLE: 7500,   // per vehicle per month
  },

  // ── Capital Gains rates (post Budget 2024) ────────────────────────────────
  CAPITAL_GAINS: {
    STCG_111A: 0.20,          // Listed equity / equity MF STCG (raised from 15% in Budget 2024)
    LTCG_112A: 0.125,         // Listed equity / equity MF LTCG (raised from 10%)
    LTCG_112A_EXEMPT: 125000, // Annual exemption (raised from ₹1L)
    LTCG_112: 0.125,          // Other LTCG without indexation
    STCG_OTHER: null,         // Taxed at slab rates
    LTCG_PROPERTY_WITH_IDX: 0.20,  // With indexation (grandfathered pre-Jul 2024)
    LTCG_PROPERTY_NO_IDX: 0.125,   // Without indexation (post Jul 2024 Budget)
    CRYPTO_VDA: 0.30,         // Section 115BBH — no deduction / set-off
    LOTTERY_115BB: 0.30,      // Lottery / game show winnings
    BONDS_54EC_EXEMPT: 5000000, // Max exemption under Sec 54EC (₹50L)
  },

  // ── Advance Tax schedule ─────────────────────────────────────────────────
  ADVANCE_TAX: [
    { installment: 1, dueDate: "15 June",      cumPct: 0.15 },
    { installment: 2, dueDate: "15 September", cumPct: 0.45 },
    { installment: 3, dueDate: "15 December",  cumPct: 0.75 },
    { installment: 4, dueDate: "15 March",     cumPct: 1.00 },
  ],


};
