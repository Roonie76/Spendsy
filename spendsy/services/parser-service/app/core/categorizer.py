from __future__ import annotations

import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class CorrectionStore:
    """
    Global store for user-provided category corrections.
    Matches are performed on normalized descriptions to ensure resilience against minor variations.
    """
    _corrections: Dict[str, str] = {} # Normalized Description -> Corrected Category

    @classmethod
    def add_correction(cls, description: str, category: str):
        """Add or update a correction for a specific transaction description."""
        norm = cls._normalize(description)
        if norm:
            cls._corrections[norm] = category
            logger.info(f"CorrectionStore: added rule '{norm}' -> {category}")

    @classmethod
    def get_correction(cls, description: str) -> Optional[str]:
        """Check if a correction exists for the given description."""
        norm = cls._normalize(description)
        return cls._corrections.get(norm)

    @staticmethod
    def _normalize(desc: str) -> str:
        """Normalize description by removing numbers, special characters, and extra spaces."""
        d = desc.upper()
        # Remove anything that's not a letter or space (e.g., dates, transaction IDs, amounts)
        d = re.sub(r'[^A-Z\s]', '', d)
        # Collapse whitespace
        return " ".join(d.split())

_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Income/Salary", [r"\bsalary\b", r"\bpayroll\b", r"\bstipend\b", r"\brefund\b", r"\bcashback\b", r"\bdividend\b", r"\binterest\s+credit\b", r"\breward[s]?\b"]),
    ("Food & Dining", [r"\bswiggy\b", r"\bzomato\b", r"\bubereats\b", r"\brestaurant\b", r"\bcafe\b", r"\bdiner\b", r"\bdominos?\b", r"\bpizza\b", r"\bmcdonald\b", r"\bkfc\b", r"\bsubway\b", r"\bbiryani\b", r"\bfood\b", r"\bgocery\b", r"\bsupermark\b", r"\bbigbasket\b", r"\bgrofers?\b", r"\bblinkc?it\b", r"\bzepto\b"]),
    ("Transport", [r"\buber\b", r"\bola\b", r"\brapido\b", r"\bfuel\b", r"\bpetrol\b", r"\bdiesel\b", r"\bparking\b", r"\bmetro\b", r"\bbus\b", r"\bauto\b", r"\birctc\b", r"\brailway\b", r"\btrain\b", r"\bcab\b", r"\btaxi\b"]),
    ("Utilities", [r"\belectricity\b", r"\bbescom\b", r"\bmsedcl\b", r"\btata\s*power\b", r"\bgas\b", r"\bindane\b", r"\bhp\s*gas\b", r"\bbharat\s*gas\b", r"\bwater\b", r"\brecharge\b", r"\bmobile\b", r"\bbroadband\b", r"\binternet\b", r"\bwifi\b", r"\bjio\b", r"\bairtel\b", r"\bbsnl\b", r"\bvi\b"]),
    ("Entertainment", [r"\bnetflix\b", r"\bamazon\s*prime\b", r"\bprime\s*video\b", r"\bhotstar\b", r"\bdisney\b", r"\bspotify\b", r"\byt\s*premium\b", r"\byoutube\s*premium\b", r"\bcinema\b", r"\bpvr\b", r"\binox\b", r"\bgaming\b", r"\bsteam\b", r"\bplaystation\b", r"\bxbox\b"]),
    ("Healthcare", [r"\bpharmacy\b", r"\bmedical\b", r"\blab\b", r"\bhospital\b", r"\bclinic\b", r"\bdoctor\b", r"\bapollo\b", r"\bfortis\b", r"\bmanipal\b", r"\bnetmeds\b", r"\b1mg\b", r"\bpharmeasy\b"]),
    ("Shopping", [r"\bamazon\b", r"\bflipkart\b", r"\bmeesho\b", r"\bshopping\b", r"\bajio\b", r"\bmyntra\b", r"\bnykaa\b", r"\breliance\s*retail\b", r"\bd[\s-]?mart\b", r"\bmart\b", r"\bstore\b"]),
    ("Travel", [r"\bflight\b", r"\bairline[s]?\b", r"\bindigo\b", r"\bair\s*india\b", r"\bspicejet\b", r"\bhotel\b", r"\bresort\b", r"\bgoibibo\b", r"\bmakemytrip\b", r"\bcleartri?p\b"]),
    ("Education", [r"\bschool\b", r"\bcollege\b", r"\buniversity\b", r"\btuition\b", r"\bcourse\b", r"\budemy\b", r"\bcoursera\b", r"\bbooks?\b", r"\bstationery\b"]),
    ("Finance", [r"\bemi\b", r"\bloan\b", r"\binsurance\b", r"\bpremium\b", r"\bcharge[s]?\b", r"\bfee[s]?\b", r"\bpenalty\b", r"\binterest\b", r"\bmutual\s*fund\b", r"\bsip\b", r"\bstock[s]?\b", r"\bdemat\b", r"\bnse\b", r"\bbse\b"]),
    ("Transfer", [r"\bneft\b", r"\brtgs\b", r"\bimps\b", r"\bupi\b", r"\btransfer\b", r"\bpay\s*to\b", r"\bsent\s*to\b", r"\bpayment\s*to\b"]),
]

_COMPILED_RULES = [(cat, [re.compile(pat, re.IGNORECASE) for pat in patterns]) for cat, patterns in _CATEGORY_RULES]

import httpx
from fuzzywuzzy import process, fuzz
from app.core.config import settings

class TransactionCategorizer:
    DEFAULT_CATEGORY = "Other"

    def categorize(self, description: str) -> str:
        """
        Assign a category based on stored feedback, rule-based patterns, 
        fuzzy matching, or AI fallback.
        """
        if not description:
            return self.DEFAULT_CATEGORY

        # 1. FEEDBACK LOOP: Check for user corrections first
        correction = CorrectionStore.get_correction(description)
        if correction:
            return correction

        # 2. RULE-BASED: Falling back to keyword matching
        norm_desc = description.upper()
        for category, patterns in _COMPILED_RULES:
            for pat in patterns:
                if pat.search(norm_desc):
                    return category

        # 3. FUZZY MATCHING: Check similarity with major brand keywords
        # Extract all keywords from all rules into a flat list for fuzzy searching
        all_keywords = []
        for cat, patterns in _CATEGORY_RULES:
            # Strip \b and lower etc
            clean_pats = [p.replace(r"\b", "").replace(r"[s]?", "s").strip() for p in patterns]
            for p in clean_pats:
                all_keywords.append((p, cat))
        
        # Search for the best fuzzy match
        choices = [k[0] for k in all_keywords]
        best_match, score = process.extractOne(description.lower(), choices, scorer=fuzz.partial_ratio)
        if score > 85: # High confidence fuzzy match
            for kw, cat in all_keywords:
                if kw == best_match:
                    logger.info(f"FuzzyCategorizer: matched '{description}' to '{best_match}' -> {cat} (score={score})")
                    return cat

        # 4. AI FALLBACK: If local rules fail, ask the AI service
        try:
            # We don't want to block the pipeline for too long, so use a tight timeout
            with httpx.Client(timeout=2.0) as client:
                resp = client.post(
                    f"{settings.ai_service_url}/insights",
                    headers={"X-Internal-API-Key": settings.internal_api_key},
                    json={
                        "prompt": f"Categorize this bank transaction description: '{description}'. Return ONLY the category name from this list: {', '.join([c[0] for c in _CATEGORY_RULES])}.",
                        "response_format": "text"
                    }
                )
                if resp.status_code == 200:
                    ai_cat = resp.json().get("output", "").strip()
                    # Validate that AI returned a valid category
                    valid_cats = [c[0] for c in _CATEGORY_RULES]
                    if ai_cat in valid_cats:
                        logger.info(f"AICategorizer: matched '{description}' -> {ai_cat}")
                        return ai_cat
        except Exception as e:
            logger.debug(f"AICategorizer failed: {e}")

        return self.DEFAULT_CATEGORY

    def annotate(self, transactions: list[Any]) -> list[Any]:
        annotated = []
        for tx in transactions:
            desc = getattr(tx, "description", "") or ""
            cat = self.categorize(desc)
            try:
                if hasattr(tx, "model_copy"):
                    annotated.append(tx.model_copy(update={"category": cat}))
                else:
                    import copy
                    tx_copy = copy.copy(tx)
                    tx_copy.category = cat
                    annotated.append(tx_copy)
            except Exception:
                try:
                    object.__setattr__(tx, "category", cat)
                except Exception: pass
                annotated.append(tx)
        return annotated
