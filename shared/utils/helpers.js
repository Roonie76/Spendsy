import { CATEGORIES, CURRENCY_SYMBOL } from '../config/constants';

// --- ID GENERATOR ---
export const generateId = () => {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    throw new Error("No crypto");
  } catch (e) {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  }
};

// --- DATE NORMALIZER ---
// Returns a valid Date or null. Callers must handle null (show "Unknown")
// rather than silently stamping today — that's what masked the parser miss
// where every parsed row displayed 4/23/2026.
//
// IMPORTANT: bare ISO date strings like "2026-04-30" are parsed by the JS
// Date constructor as UTC midnight, which shifts them back by one calendar day
// for any timezone west of UTC. We detect that pattern and parse as LOCAL time
// instead, so date comparisons in chart filters are always correct.
export const normalizeDate = (d) => {
  if (!d) return null;
  if (d instanceof Date) return isNaN(d.getTime()) ? null : d;
  if (d.seconds) return new Date(d.seconds * 1000); // Firestore Timestamp

  // Pure date strings "YYYY-MM-DD" — parse as local midnight to avoid UTC shift
  if (typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d)) {
    const [year, month, day] = d.split('-').map(Number);
    return new Date(year, month - 1, day); // local midnight — no UTC offset
  }

  const parsed = new Date(d);
  return isNaN(parsed.getTime()) ? null : parsed;
};

/**
 * --- LOCAL DATE FORMATTER ---
 * Converts a Date object (or Date string) to YYYY-MM-DD string in LOCAL time.
 * This avoids the common bug where .toISOString() shifts the date to UTC,
 * causing 12am-5am transactions to appear as the previous day.
 */
export const formatLocalDate = (d) => {
  const date = normalizeDate(d) || new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// --- SCRIPT LOADER (For PDF.js / Tesseract) ---
export const loadScript = (src) => new Promise((resolve, reject) => {
  if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
  const script = document.createElement('script'); 
  script.src = src; 
  script.onload = resolve; 
  script.onerror = reject; 
  document.head.appendChild(script);
});

// --- CURRENCY FORMATTER (Fixed Symbol) ---
export const formatIndianCompact = (num) => {
  const val = parseFloat(num) || 0;
  const absVal = Math.abs(val);

  if (absVal >= 10000000) return `${CURRENCY_SYMBOL}${(val / 10000000).toFixed(2)} Cr`;
  if (absVal >= 100000) return `${CURRENCY_SYMBOL}${(val / 100000).toFixed(2)} L`;
  if (absVal >= 1000) return `${CURRENCY_SYMBOL}${(val / 1000).toFixed(1)} k`; // Added 'k' support
  
  return `${CURRENCY_SYMBOL}${val.toLocaleString('en-IN')}`;
};

// --- FINANCIAL YEAR CALCULATOR ---
export const getCurrentFinancialYear = () => {
  const now = new Date();
  const currentYear = now.getFullYear();
  // If month is Jan(0), Feb(1), or Mar(2), we are in previous FY's end.
  return now.getMonth() >= 3 ? `${currentYear}-${currentYear + 1}` : `${currentYear - 1}-${currentYear}`;
};

// --- SMART AUTO-CATEGORIZER ---
// This aligns with the new ParserService to detect categories automatically
export const categorizeTransaction = (desc) => {
    if (!desc) return 'other';
    const d = desc.toLowerCase();

    // 1. Food
    if (d.match(/zomato|swiggy|kfc|mcdonald|burger|pizza|restaurant|cafe|coffee|starbucks|domino|biryani|fresh|food/)) return 'food';
    
    // 2. Transport
    if (d.match(/uber|ola|rapido|fuel|petrol|pump|shell|hpcl|bpcl|parking|toll|fastag|metro|train|irctc|flight|air|indigo/)) return 'transport';
    
    // 3. Shopping
    if (d.match(/amazon|flipkart|myntra|ajio|zara|h&m|uniqlo|decathlon|ikea|chroma|reliance|mart|store|retail|shop/)) return 'shopping';
    
    // 4. Bills/Utilities
    if (d.match(/bill|electricity|bescom|water|gas|broadband|wifi|jio|airtel|vi|vodafone|bsnl|recharge|mobile|dth|tatasky/)) return 'utilities';
    
    // 5. Entertainment
    if (d.match(/netflix|spotify|prime|hotstar|bookmyshow|pvr|inox|cinema|movie|game|steam|playstation/)) return 'entertainment';
    
    // 6. Health
    if (d.match(/pharmacy|medical|hospital|clinic|doctor|lab|diag|medplus|apollo|1mg|practo|health/)) return 'health';

    // 7. Salary
    if (d.match(/salary|payroll|stipend/)) return 'salary';

    // 8. Investment
    if (d.match(/zerodha|groww|upstox|kite|angel|sip|mutual|fund|stock|trade|invest|ppf|nps|lic/)) return 'investment';

    // Fallback: Check if CATEGORIES constant has keywords (if you added them there)
    for (const c of CATEGORIES) { 
        if (c.keywords && c.keywords.some(k => d.includes(k))) return c.id; 
    }

    return 'other';
};

// --- AUTH HEADER BUILDER ---
// Supports DRF Token auth and JWT Bearer auth.
export const buildAuthHeader = (token) => {
  if (!token) return null;
  const trimmed = String(token).trim();
  if (!trimmed) return null;
  const lower = trimmed.toLowerCase();
  if (lower.startsWith('bearer ') || lower.startsWith('token ')) return trimmed;

  const isJwt = trimmed.split('.').length === 3;
  return `${isJwt ? 'Bearer' : 'Token'} ${trimmed}`;
};
