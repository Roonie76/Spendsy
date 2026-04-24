"""Realistic Indian-user query generator for TORA stress testing.

Produces ~1200 queries by crossing:
  - 20 personas (age, city, surplus, life stage)
  - 12 plugin categories + 6 track-1 intents + 3 adversarial intents
  - 3 phrasing styles: clean English (55%), Hinglish/Hindi (30%), typos/casual (15%)

Each query comes with ground-truth labels so the report can measure
resolver accuracy per category and per style.

Seeded for reproducibility — same seed = same corpus, so regressions are
comparable across engine revisions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Persona:
    """A realistic Indian user persona. Used to template surplus/city/age
    into queries so 'can I afford X' has a grounded user context."""
    name: str
    age: int
    city: str
    monthly_income: int
    monthly_surplus: int
    life_stage: str  # "student" | "early_career" | "mid_career" | "senior" | "retired"


PERSONAS: list[Persona] = [
    Persona("Rohan (Bangalore SDE)",        27, "bangalore",  95_000,  28_000, "early_career"),
    Persona("Anjali (Mumbai analyst)",      25, "mumbai",     75_000,  12_000, "early_career"),
    Persona("Kiran (Hyderabad consultant)", 32, "hyderabad", 180_000,  65_000, "mid_career"),
    Persona("Meera (Delhi teacher)",        35, "delhi_ncr",  55_000,   8_000, "mid_career"),
    Persona("Arjun (Pune startup founder)", 29, "pune",      120_000,  45_000, "mid_career"),
    Persona("Priya (Chennai doctor)",       34, "chennai",   140_000,  50_000, "mid_career"),
    Persona("Vikram (Kolkata shopkeeper)",  48, "kolkata",    70_000,  15_000, "senior"),
    Persona("Sanjay (Ahmedabad CA)",        42, "ahmedabad",  95_000,  38_000, "senior"),
    Persona("Divya (Noida banker)",         30, "delhi_ncr", 110_000,  30_000, "mid_career"),
    Persona("Nikhil (Mumbai architect)",    38, "mumbai",    160_000,  40_000, "senior"),
    Persona("Swathi (Bangalore designer)",  26, "bangalore",  68_000,  18_000, "early_career"),
    Persona("Ravi (Chennai trader)",        45, "chennai",   200_000,  80_000, "senior"),
    Persona("Anita (Pune IT manager)",      40, "pune",      180_000,  55_000, "senior"),
    Persona("Zara (Delhi content creator)", 24, "delhi_ncr",  45_000,   5_000, "early_career"),
    Persona("Manish (Tier2 schoolteacher)", 36, "tier2",      42_000,   6_000, "mid_career"),
    Persona("Kavita (Gurgaon HR lead)",     33, "delhi_ncr", 130_000,  42_000, "mid_career"),
    Persona("Siddharth (Mumbai investor)",  55, "mumbai",    350_000, 180_000, "senior"),
    Persona("Tara (student doing MBA)",     23, "bangalore",  25_000,   2_000, "student"),
    Persona("Rajesh (retired govt officer)",65, "delhi_ncr",  80_000,  25_000, "retired"),
    Persona("Farida (Hyderabad dentist)",   37, "hyderabad", 165_000,  60_000, "senior"),
]


# ---------------------------------------------------------------------------
# Ground-truth labels
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryLabel:
    """Ground truth attached to every generated query."""
    track: int                    # 1 = profile-only, 2 = universal intelligence
    expected_plugin: str | None   # e.g. "mobility"; None for track 1
    category_tag: str             # broader bucket for coverage reports
    style: str                    # "english" | "hinglish" | "typos"
    should_enable_thinking: bool  # expected thinking-mode decision


@dataclass
class GeneratedQuery:
    text: str
    persona: Persona
    label: QueryLabel


# ---------------------------------------------------------------------------
# Template pools — one block per plugin + track-1 + adversarial
# Each template is a lambda taking (persona) and returning a string, so we
# can inject realistic surplus/city into the phrasing.
# ---------------------------------------------------------------------------


TEMPLATES_MOBILITY: list[tuple[str, str]] = [
    # (template, style)
    ("can i afford a new car on my salary", "english"),
    ("is a Swift or a used sedan better for me", "english"),
    ("bike loan EMI for 1.5 lakh bike", "english"),
    ("should i buy an EV or a petrol car", "english"),
    ("how much will my monthly fuel cost be", "english"),
    ("planning to buy a scooter, what's the on-road cost", "english"),
    ("should i finance or pay cash for a bike", "english"),
    ("tell me about electric scooter subsidies", "english"),
    ("auto loan interest rate comparison", "english"),
    # Hinglish
    ("nayi gaadi lene ke liye loan kaisa milega", "hinglish"),
    ("scooty ya bike, kya lu", "hinglish"),
    ("Swift kitne ki aati hai on road", "hinglish"),
    ("EV bike ke liye subsidy hai kya abhi", "hinglish"),
    ("mere surplus me EMI afford kar sakta hu kya", "hinglish"),
    # Typos / casual
    ("can i aford a swuft", "typos"),
    ("bike ka emi calculate kroo", "typos"),
    ("shd i buy ev", "typos"),
]

TEMPLATES_REAL_ESTATE: list[tuple[str, str]] = [
    ("how much home loan can i get on my salary", "english"),
    ("buying a 2BHK in Bangalore, is it worth it", "english"),
    ("rent vs buy, which is better for me", "english"),
    ("what's the stamp duty in Maharashtra", "english"),
    ("average rent for a 2BHK in Pune", "english"),
    ("should i invest in a plot in tier 2 city", "english"),
    ("EMI for 80 lakh home loan over 20 years", "english"),
    ("under construction vs ready possession tax wise", "english"),
    ("can i afford a flat in mumbai", "english"),
    # Hinglish
    ("flat kharidu ya rent pe rahu", "hinglish"),
    ("Mumbai me 1 BHK kitne ka milega", "hinglish"),
    ("home loan ke liye kitna down payment chahiye", "hinglish"),
    ("zameen kharidni chahiye kya abhi", "hinglish"),
    ("kiraya dena sasta hai ya EMI", "hinglish"),
    # Typos
    ("how mch home lon", "typos"),
    ("rnt vs buy", "typos"),
]

TEMPLATES_ELECTRONICS: list[tuple[str, str]] = [
    ("should i wait for Big Billion sale to buy a laptop", "english"),
    ("MacBook Air vs a Windows laptop in my budget", "english"),
    ("iPhone vs a flagship Android under 80k", "english"),
    ("is now a good time to buy a laptop", "english"),
    ("best phone under 30000 rupees", "english"),
    ("gaming laptop on EMI, worth it", "english"),
    ("should i buy a new iPad or used", "english"),
    ("smartwatch worth the cost", "english"),
    # Hinglish
    ("laptop abhi lu ya sale ka wait karu", "hinglish"),
    ("iPhone sasta kab hota hai", "hinglish"),
    ("Flipkart sale me phone kitna sasta hota hai", "hinglish"),
    ("camera lena chahiye photography ke liye", "hinglish"),
    # Typos
    ("shud i wait for big billon sale", "typos"),
    ("iphne vs androd", "typos"),
]

TEMPLATES_APPLIANCES: list[tuple[str, str]] = [
    ("when is the best time to buy an AC", "english"),
    ("1.5 ton split AC under 50000", "english"),
    ("should i buy a front load washing machine", "english"),
    ("55 inch smart TV recommendations for diwali sale", "english"),
    ("fridge double door budget", "english"),
    ("5 star AC vs 3 star, is the extra cost worth it", "english"),
    ("microwave or OTG, which is better", "english"),
    ("geyser for 4 people bathroom", "english"),
    # Hinglish
    ("AC abhi lu ya winter me cheap hoga", "hinglish"),
    ("TV Diwali sale me kitne me milega", "hinglish"),
    ("washing machine front load ya top load", "hinglish"),
    # Typos
    ("when is ac chepest", "typos"),
    ("55in tv diwali sale", "typos"),
]

TEMPLATES_TRAVEL: list[tuple[str, str]] = [
    ("planning a Europe trip in 6 months, how much to save", "english"),
    ("Goa trip for 4 people budget", "english"),
    ("should i go to Dubai or Thailand for vacation", "english"),
    ("USA trip cost estimate for 2 weeks", "english"),
    ("visa fees for Schengen countries", "english"),
    ("forex card vs debit card abroad", "english"),
    ("honeymoon package Maldives vs Bali", "english"),
    ("domestic flight prices for Delhi to Goa", "english"),
    ("travel insurance for USA trip", "english"),
    # Hinglish
    ("Europe trip ke liye kitna save karna padega", "hinglish"),
    ("Thailand 1 hafte ka kitna lagega", "hinglish"),
    ("honeymoon ke liye budget plan karo", "hinglish"),
    ("Dubai ya Singapore, konsa cheaper hoga", "hinglish"),
    # Typos
    ("euro trip cst", "typos"),
    ("thailnd vacaton budget", "typos"),
]

TEMPLATES_GOLD: list[tuple[str, str]] = [
    ("should i buy gold this Diwali", "english"),
    ("gold today rate for 10 grams 22K", "english"),
    ("SGB vs physical gold which is better investment", "english"),
    ("making charges on gold jewellery", "english"),
    ("silver vs gold investment", "english"),
    ("diamond price for 1 carat", "english"),
    ("is gold a good hedge against inflation", "english"),
    ("digital gold safe to invest in", "english"),
    # Hinglish
    ("sona abhi kharidu ya wait karu", "hinglish"),
    ("Diwali par gold sasta hoga kya", "hinglish"),
    ("SGB kya hota hai aur isme paisa lagana chahiye", "hinglish"),
    ("gehne banwaun ya SGB me invest karu", "hinglish"),
    # Typos
    ("gold now rate 22k", "typos"),
    ("sgb vs jewelry", "typos"),
]

TEMPLATES_INVESTMENTS: list[tuple[str, str]] = [
    ("should i start a SIP with 5000 per month", "english"),
    ("SIP vs FD which gives better returns", "english"),
    ("best tax saving investment under 80C", "english"),
    ("PPF vs ELSS for long term", "english"),
    ("NPS tier 1 returns for retirement", "english"),
    ("large cap vs mid cap mutual fund", "english"),
    ("how much to invest for 1 crore in 15 years", "english"),
    ("FD interest rates SBI vs HDFC", "english"),
    ("stock market down, should i invest more", "english"),
    ("how to reduce my income tax legally", "english"),
    ("ELSS lock in period questions", "english"),
    # Hinglish
    ("SIP ya FD, kya better hai", "hinglish"),
    ("80C tax saving ke liye kya best hai", "hinglish"),
    ("mutual fund me paisa lagana safe hai kya", "hinglish"),
    ("PPF me 1.5 lakh dalu ya ELSS me", "hinglish"),
    ("retirement ke liye kitna save karna hoga", "hinglish"),
    # Typos
    ("sip vs fd retrn", "typos"),
    ("ppf v elss", "typos"),
]

TEMPLATES_EDUCATION: list[tuple[str, str]] = [
    ("cost of MBA in IIM vs private tier 1", "english"),
    ("education loan interest rates for USA MS", "english"),
    ("coaching fees for UPSC preparation", "english"),
    ("IELTS GRE prep cost", "english"),
    ("MS in USA total budget estimate", "english"),
    ("CAT coaching is it worth the fees", "english"),
    ("should i do MBA in India or abroad", "english"),
    ("cost of living for student in London", "english"),
    ("scholarship options for study abroad", "english"),
    # Hinglish
    ("MBA ke liye IIM ya private lu", "hinglish"),
    ("abroad masters ke liye kitna paisa chahiye", "hinglish"),
    ("UPSC coaching ka fees kitna hai Delhi me", "hinglish"),
    ("education loan ke tax benefits kya hai", "hinglish"),
    # Typos
    ("mba in iim fees", "typos"),
    ("ms usa cst", "typos"),
]

TEMPLATES_HEALTHCARE: list[tuple[str, str]] = [
    ("best health insurance for family of 4", "english"),
    ("how much cover do i need at age 35", "english"),
    ("knee replacement surgery cost in India", "english"),
    ("term life insurance for 1 crore", "english"),
    ("senior citizen health insurance plans", "english"),
    ("IVF treatment total cost", "english"),
    ("dental implant charges", "english"),
    ("what's covered under 80D deduction", "english"),
    ("normal vs c-section delivery charges", "english"),
    # Hinglish
    ("health insurance kitne ka lu family floater", "hinglish"),
    ("dental treatment ka kitna kharcha hoga", "hinglish"),
    ("parents ke liye mediclaim le lu", "hinglish"),
    ("surgery ka kharcha kaise cover karu", "hinglish"),
    # Typos
    ("health insurnce family 4", "typos"),
    ("term plan 1cr", "typos"),
]

TEMPLATES_WEDDING: list[tuple[str, str]] = [
    ("my wedding budget for 200 guests", "english"),
    ("destination wedding vs city wedding cost", "english"),
    ("how much should i save for marriage in 2 years", "english"),
    ("bridal jewellery budget mid range", "english"),
    ("photography package for wedding", "english"),
    ("honeymoon for Europe budget", "english"),
    ("reception venue cost in Delhi", "english"),
    ("is taking a loan for wedding a good idea", "english"),
    # Hinglish
    ("shaadi ka budget 10 lakh me ho jaega kya", "hinglish"),
    ("destination wedding Goa me kitna kharcha hoga", "hinglish"),
    ("photographer ka package kitne ka milega", "hinglish"),
    ("reception venue Delhi me cheap kahan milega", "hinglish"),
    ("sangeet ka budget plan karo", "hinglish"),
    # Typos
    ("shaadi budet 200 guests", "typos"),
    ("bridal jewellry budget", "typos"),
]

TEMPLATES_FURNITURE: list[tuple[str, str]] = [
    ("cost to renovate my kitchen 100 sqft", "english"),
    ("modular kitchen vs carpenter built", "english"),
    ("sofa set budget for 3BHK", "english"),
    ("paint my 2BHK, total cost", "english"),
    ("bathroom renovation cost breakdown", "english"),
    ("buy new furniture or rent", "english"),
    ("wardrobe sliding custom design cost", "english"),
    # Hinglish
    ("kitchen renovate karwana hai, kitna kharcha hoga", "hinglish"),
    ("modular kitchen ka total cost Bangalore me", "hinglish"),
    ("2 BHK paint karwana hai cost", "hinglish"),
    ("sofa set 5 seater budget", "hinglish"),
    # Typos
    ("kitchen reno 100sqft", "typos"),
    ("modlar ktchen cost", "typos"),
]

TEMPLATES_LIFESTYLE: list[tuple[str, str]] = [
    ("am i spending too much on Netflix and Spotify", "english"),
    ("monthly subscription total, should i cut down", "english"),
    ("cult fit vs local gym membership", "english"),
    ("food delivery addiction, how much am i spending", "english"),
    ("which OTT plan is worth keeping", "english"),
    ("annual vs monthly subscription which is cheaper", "english"),
    # Hinglish
    ("OTT subscriptions pe kitna spend ho raha hai", "hinglish"),
    ("gym join karu ya home workout", "hinglish"),
    ("Netflix Prime dono chahiye kya", "hinglish"),
    ("Swiggy Zomato pe kharcha control karu kaise", "hinglish"),
    # Typos
    ("netflx spotify mnthly", "typos"),
    ("gym membrship cost", "typos"),
]

# Track-1 queries: profile-only, expect NO plugin match
TEMPLATES_TRACK_1: list[tuple[str, str, str]] = [
    # (template, style, intent_tag)
    ("how much did i spend on food this month",        "english", "spending_query"),
    ("what is my savings rate",                         "english", "savings_query"),
    ("where did my money go last week",                 "english", "spending_query"),
    ("total expense this month",                        "english", "spending_query"),
    ("my monthly income vs expenses",                   "english", "balance_query"),
    ("am i spending more than my budget",               "english", "budget_query"),
    ("how much can i save if i cut dining out",         "english", "savings_query"),
    ("show me biggest expenses this month",             "english", "spending_query"),
    ("current account balance",                         "english", "balance_query"),
    ("when did i last get a salary credit",             "english", "income_query"),
    ("mere kitne paise bache is month",                 "hinglish", "savings_query"),
    ("food pe kitna gaya",                              "hinglish", "spending_query"),
    ("kitna spend kiya shopping pe",                    "hinglish", "spending_query"),
    ("balance dikhao",                                  "hinglish", "balance_query"),
    ("monthly budget me kitna bacha",                   "hinglish", "budget_query"),
    ("how mch did i spend",                             "typos", "spending_query"),
    ("sav rate mine",                                   "typos", "savings_query"),
    ("this mnth expense total",                         "typos", "spending_query"),
]

# Adversarial / edge cases: should produce predictable no-match or graceful behavior
TEMPLATES_ADVERSARIAL: list[tuple[str, str, str]] = [
    ("hi tora",                              "english", "greeting"),
    ("thanks for the help",                  "english", "small_talk"),
    ("what can you do",                      "english", "capability"),
    ("tell me a joke",                       "english", "off_topic"),
    ("what's the weather today",             "english", "off_topic"),
    ("",                                      "english", "empty"),
    ("????",                                  "english", "garbage"),
    ("evening",                               "english", "trap_ev"),  # should NOT match 'ev'
    ("every month i spend more",              "english", "trap_ev"),
    ("I have too many tvs in my house for the guests",  "english", "trap_tv"),
]


PLUGIN_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "mobility":     TEMPLATES_MOBILITY,
    "real_estate":  TEMPLATES_REAL_ESTATE,
    "electronics":  TEMPLATES_ELECTRONICS,
    "appliances":   TEMPLATES_APPLIANCES,
    "travel":       TEMPLATES_TRAVEL,
    "gold":         TEMPLATES_GOLD,
    "investments":  TEMPLATES_INVESTMENTS,
    "education":    TEMPLATES_EDUCATION,
    "healthcare":   TEMPLATES_HEALTHCARE,
    "wedding":      TEMPLATES_WEDDING,
    "furniture":    TEMPLATES_FURNITURE,
    "lifestyle":    TEMPLATES_LIFESTYLE,
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def generate_corpus(n_target: int = 1200, seed: int = 42) -> list[GeneratedQuery]:
    """Produce a deterministic corpus of ~`n_target` queries.

    Split roughly:
      - 70% track-2 plugin queries (evenly across 12 plugins)
      - 20% track-1 queries
      - 10% adversarial

    Every query is paired with a persona so downstream scenario-aware
    reasoning has grounded context.
    """
    rng = random.Random(seed)

    queries: list[GeneratedQuery] = []

    # Track 2 — plugin queries
    track2_target = int(n_target * 0.70)
    per_plugin = track2_target // len(PLUGIN_TEMPLATES)
    for plugin_id, templates in PLUGIN_TEMPLATES.items():
        for _ in range(per_plugin):
            template, style = rng.choice(templates)
            persona = rng.choice(PERSONAS)
            queries.append(
                GeneratedQuery(
                    text=template,
                    persona=persona,
                    label=QueryLabel(
                        track=2,
                        expected_plugin=plugin_id,
                        category_tag=plugin_id,
                        style=style,
                        should_enable_thinking=True,
                    ),
                )
            )

    # Track 1 — profile-only
    track1_target = int(n_target * 0.20)
    for _ in range(track1_target):
        template, style, tag = rng.choice(TEMPLATES_TRACK_1)
        persona = rng.choice(PERSONAS)
        queries.append(
            GeneratedQuery(
                text=template,
                persona=persona,
                label=QueryLabel(
                    track=1,
                    expected_plugin=None,
                    category_tag=tag,
                    style=style,
                    should_enable_thinking=False,
                ),
            )
        )

    # Adversarial — 10%
    adv_target = n_target - len(queries)
    for _ in range(adv_target):
        template, style, tag = rng.choice(TEMPLATES_ADVERSARIAL)
        persona = rng.choice(PERSONAS)
        queries.append(
            GeneratedQuery(
                text=template,
                persona=persona,
                label=QueryLabel(
                    track=1,
                    expected_plugin=None,
                    category_tag=tag,
                    style=style,
                    should_enable_thinking=False,
                ),
            )
        )

    rng.shuffle(queries)
    return queries


def summarize_corpus(corpus: list[GeneratedQuery]) -> dict[str, Any]:
    """Quick inventory of what we generated — handy for the report header."""
    by_category: dict[str, int] = {}
    by_style: dict[str, int] = {}
    by_track: dict[int, int] = {}
    for q in corpus:
        by_category[q.label.category_tag] = by_category.get(q.label.category_tag, 0) + 1
        by_style[q.label.style] = by_style.get(q.label.style, 0) + 1
        by_track[q.label.track] = by_track.get(q.label.track, 0) + 1
    return {
        "total": len(corpus),
        "by_track": by_track,
        "by_style": by_style,
        "by_category": dict(sorted(by_category.items())),
        "distinct_personas": len({q.persona.name for q in corpus}),
    }
