import { CATEGORIES } from '../config/constants';

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
export const normalizeDate = (d) => {
  if (!d) return new Date();
  if (d.seconds) return new Date(d.seconds * 1000); // Handle Firestore Timestamp
  return new Date(d);
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

  if (absVal >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
  if (absVal >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
  if (absVal >= 1000) return `₹${(val / 1000).toFixed(1)} k`; // Added 'k' support
  
  return `₹${val.toLocaleString('en-IN')}`;
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
    if (!desc) return 'others';
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
