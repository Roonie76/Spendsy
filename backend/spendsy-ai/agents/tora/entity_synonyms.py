"""
Hand-curated synonym map: user phrase → canonical entity key.

Includes Hindi/Hinglish variants common in Indian personal-finance conversation.
Keys are lowercased; matching is token-based so multi-word phrases are matched
as consecutive tokens, not as substrings.

Keep this file as the single source of truth for synonyms — plugin modules
declare only canonical `entity_keys`, never their own synonym lists.
"""

# Each entry: canonical_entity → list of synonyms (including common misspellings,
# Hindi/Hinglish, and plural/singular variants the resolver's token matcher
# won't already catch).
SYNONYMS: dict[str, list[str]] = {
    # --- Mobility ---
    "car": ["car", "cars", "gaadi", "gaddi", "four wheeler", "4 wheeler", "sedan",
            "hatchback", "suv", "mpv", "compact suv",
            # loans + fuel (missed in v1 corpus)
            "auto loan", "auto loan rate", "car loan", "fuel cost",
            "petrol cost", "diesel cost", "monthly fuel",
            # popular models — keep short, Indian-market common
            "swift", "i20", "baleno", "creta", "seltos", "nexon", "venue",
            "ertiga", "innova", "thar", "brezza", "dzire", "wagonr"],
    "bike": ["bike", "bikes", "motorcycle", "motorbike", "two wheeler",
             "2 wheeler", "scooter", "scooty", "activa", "bike loan",
             "bike emi", "pulsar", "splendor", "fz", "classic 350"],
    "ev": ["ev", "electric vehicle", "electric car", "electric bike",
           "electric scooter", "e bike", "e scooter", "ola electric",
           "ather", "ev subsidy"],
    "truck": ["truck", "tempo", "commercial vehicle", "lorry"],

    # --- Real estate ---
    # Note: bare "home" NOT in the list because "home gym", "home workout"
    # are lifestyle queries. "home loan" is still matched explicitly below.
    "house": ["house", "houses", "ghar", "makaan", "flat", "apartment",
              "apartments", "villa", "bungalow", "bhk", "1bhk", "2bhk",
              "3bhk", "4bhk", "property"],
    "home loan": ["home loan", "home loans", "housing loan", "mortgage"],
    "plot": ["plot", "land", "zameen", "site", "residential plot"],
    "rent": ["rent", "rental", "rented", "rent out", "on rent", "kiraya"],
    "office space": ["office space", "commercial space", "shop", "showroom"],
    "stamp duty": ["stamp duty", "registration fee", "registration charges",
                   "stamp and registration"],
    "under construction": ["under construction", "ready possession",
                           "ready to move", "new construction", "occupancy"],

    # --- Electronics ---
    "laptop": ["laptop", "laptops", "notebook", "macbook", "chromebook",
               "gaming laptop", "ultrabook"],
    "phone": ["phone", "phones", "smartphone", "mobile", "cell phone",
              "iphone", "android phone", "samsung", "oneplus", "pixel",
              "vivo", "oppo", "realme", "redmi", "nothing phone"],
    "tablet": ["tablet", "tablets", "ipad", "android tablet"],
    "camera": ["camera", "dslr", "mirrorless", "gopro"],
    "smartwatch": ["smartwatch", "smart watch", "fitness band", "fitbit",
                   "apple watch", "boat watch", "noise watch"],
    "pc": ["pc", "desktop", "gaming pc", "custom pc"],
    "monitor": ["monitor", "monitors", "display", "led monitor"],
    # "big billion", "great indian festival" → electronics sale windows
    "electronics sale": ["big billion", "big billion sale",
                         "great indian festival", "amazon sale", "flipkart sale",
                         "diwali tech sale"],

    # --- Appliances ---
    "ac": ["ac", "acs", "air conditioner", "air conditioners",
           "air conditioning", "split ac", "window ac"],
    "fridge": ["fridge", "fridges", "refrigerator", "refrigerators",
               "double door fridge"],
    "washing machine": ["washing machine", "washing machines", "front load",
                        "top load", "washer", "washers"],
    "tv": ["tv", "tvs", "television", "televisions", "smart tv", "led tv",
           "qled", "oled tv"],
    "geyser": ["geyser", "water heater"],
    "microwave": ["microwave", "oven", "otg", "microwave oven"],
    "dishwasher": ["dishwasher"],
    "chimney": ["chimney", "kitchen chimney"],
    "cooler": ["cooler", "air cooler", "desert cooler"],

    # --- Travel ---
    "trip": ["trip", "trips", "vacation", "holiday", "travel", "travelling",
             "tour", "getaway", "vacaton"],  # common typo
    "flight": ["flight", "flights", "airfare", "air ticket"],
    "hotel": ["hotel", "hotels", "stay", "accommodation", "resort"],
    "international": ["international", "abroad", "overseas", "foreign trip",
                      "videsh"],
    "europe": ["europe", "schengen", "eu trip", "paris", "rome", "london trip"],
    "usa": ["usa", "us trip", "america", "united states"],
    "dubai": ["dubai", "uae"],
    "goa": ["goa"],
    "manali": ["manali", "himachal trip"],
    "thailand": ["thailand", "bangkok", "phuket", "krabi"],
    "singapore": ["singapore", "sg trip"],
    "bali": ["bali"],
    "maldives": ["maldives"],
    "japan trip": ["japan trip", "tokyo trip", "osaka"],
    "honeymoon trip": ["honeymoon trip", "honeymoon package",
                       "honeymoon for europe", "honeymoon vacation"],
    "visa": ["visa", "visa fee", "visa fees", "schengen visa",
             "tourist visa"],
    "forex": ["forex", "forex card", "foreign exchange",
              "currency exchange", "exchange rate"],

    # --- Gold & jewellery ---
    "gold": ["gold", "sona", "24k gold", "22k gold"],
    "silver": ["silver", "chandi"],
    # Bare "jewellery" → gold plugin. "bridal jewellery" is a longer match
    # registered on WEDDING plugin, so it wins by length-preference.
    "jewellery": ["jewellery", "jewelry", "gehna", "gehne", "ornaments",
                  "necklace", "chain", "ring", "bangle", "bangles",
                  "earrings", "jhumka", "kada"],
    "diamond": ["diamond", "solitaire", "heera"],
    "platinum": ["platinum"],
    "sgb": ["sgb", "sovereign gold bond", "sovereign gold bonds",
            "gold bond", "gold etf", "digital gold"],

    # --- Investments ---
    # NOTE: bare "invest" is kept but short SGB/ELSS/etc. are preferred —
    # resolver uses longer-phrase tie-breaking so "invest in SGB" hits gold.
    "invest": ["invest", "investing", "investment", "investor", "nivesh",
               "paisa lagana", "paise lagana"],
    "stocks": ["stocks", "stock", "shares", "equity", "share market",
               "stock market"],
    "mutual fund": ["mutual fund", "mutual funds", "mf", "mfs",
                    "large cap", "mid cap", "small cap", "flexi cap",
                    "large cap fund", "mid cap fund", "small cap fund"],
    "sip": ["sip", "sips", "systematic investment plan"],
    "fd": ["fd", "fds", "fixed deposit", "fixed deposits"],
    "nps": ["nps", "national pension"],
    "bonds": ["bond", "bonds", "debenture", "debentures", "g sec", "gsec"],
    "ppf": ["ppf", "public provident fund"],
    "elss": ["elss", "tax saving fund", "tax saver fund"],
    "etf": ["etf", "etfs", "exchange traded fund", "index fund"],
    "nifty": ["nifty", "nifty50", "nifty 50"],
    "sensex": ["sensex", "bse sensex"],
    "tax saving": ["80c", "section 80c", "tax saving",
                   "income tax saving", "reduce income tax",
                   "reduce tax", "tax planning", "tax harvesting"],
    "retirement": ["retirement", "retire", "retirement corpus",
                   "retirement planning", "pension", "post retirement"],
    "income tax": ["income tax", "tax return", "itr", "tax liability"],

    # --- Education ---
    "college": ["college", "colleges", "university", "campus"],
    "course": ["course", "courses", "program", "bootcamp"],
    "mba": ["mba", "management degree"],
    "btech": ["b tech", "engineering degree"],  # removed "btech" alone and "be"
                                                # to stop false positives on
                                                # "fuel cost will be"
    "masters": ["masters", "ms", "m tech", "post graduation", "pg"],
    "phd": ["phd", "doctorate"],
    "abroad study": ["study abroad", "foreign education", "videsh padhai",
                     "abroad studies", "studies abroad", "student abroad",
                     "london study", "uk masters"],
    "coaching": ["coaching", "tuition", "classes", "test prep",
                 "coaching fees"],
    "upsc": ["upsc", "ias", "civil services"],
    "cat": ["cat exam", "cat prep"],
    "ielts": ["ielts", "toefl", "gre", "gmat"],
    "certification": ["certification", "certificate course"],
    "cost of living": ["cost of living", "living expense", "living expenses",
                       "student living", "rent abroad"],
    "education loan": ["education loan", "edu loan", "student loan",
                       "study loan", "80e"],

    # --- Healthcare ---
    "health insurance": ["health insurance", "mediclaim", "health policy",
                         "medical insurance", "family floater", "health cover",
                         "insurance cover", "sum insured", "cover amount"],
    "term insurance": ["term insurance", "term plan", "term life", "term cover",
                       "life cover", "life insurance", "1 crore cover",
                       "1cr cover", "term policy"],
    "80d deduction": ["80d", "80 d deduction", "section 80d",
                      "health insurance tax", "mediclaim tax benefit"],
    "surgery": ["surgery", "surgeries", "operation", "procedure",
                "operation theatre"],
    "hospital": ["hospital", "hospitals", "hospitalisation",
                 "hospitalization"],
    "dental": ["dental", "dentist", "teeth", "root canal", "braces",
               "dental implant"],
    "ivf": ["ivf", "fertility treatment"],
    "therapy": ["therapy", "counseling", "counselling", "mental health"],
    # gym moved to lifestyle — see overlap fix below
    "medicine": ["medicine", "medicines", "medication", "dawai"],

    # --- Wedding & events ---
    "wedding": ["wedding", "marriage", "shaadi", "shadi", "weddings",
                "wedding budget", "wedding planning", "destination wedding",
                "wedding photography", "wedding photographer",
                "wedding venue", "wedding vendor", "wedding vendors"],
    # Register multi-word terms that would otherwise hit gold/travel —
    # longer-match preference makes these win.
    "bridal jewellery": ["bridal jewellery", "bridal jewelry",
                         "wedding jewellery", "wedding jewelry",
                         "dulhan ka gehna", "shaadi ka gehna",
                         "bridal lehenga", "wedding lehenga"],
    "wedding photographer": ["wedding photography", "wedding photographer",
                             "shaadi photographer", "pre wedding shoot"],
    "reception": ["reception", "sangeet", "engagement", "mehendi",
                  "mehndi", "haldi"],
    "anniversary": ["anniversary"],
    "birthday party": ["birthday party", "birthday celebration",
                       "birthday bash"],
    "event": ["event", "function", "party", "get together"],
    # "honeymoon trip" already lives under travel with the same length,
    # so wedding-primary needs this shorter/more-generic "honeymoon" key:
    "honeymoon": ["honeymoon", "honeymoon budget", "honeymoon planning"],

    # --- Furniture & home improvement ---
    "furniture": ["furniture", "sofa", "sofas", "couch", "bed", "wardrobe",
                  "dining table", "study table", "bookshelf", "sofa set",
                  "furniture set"],
    "renovation": ["renovation", "renovations", "renovate", "renovating",
                   "reno", "remodel", "remodeling", "remodelling",
                   "interior", "interiors", "interior design"],
    "modular kitchen": ["modular kitchen", "kitchen renovation",
                        "kitchen remodel", "kitchen", "kitchens",
                        "renovate kitchen", "renovate my kitchen"],
    "paint": ["paint", "painting", "wall paint", "home paint", "house paint"],
    "flooring": ["flooring", "tiles", "marble", "wooden flooring"],
    "bathroom": ["bathroom", "bathrooms", "bathroom renovation", "washroom",
                 "toilet"],

    # --- Lifestyle & recurring ---
    "ott": ["ott", "netflix", "amazon prime", "prime video", "hotstar",
            "disney plus", "disney+", "sony liv", "zee5", "subscription",
            "subscriptions", "streaming"],
    "spotify": ["spotify", "apple music", "youtube music",
                "music subscription"],
    "dining": ["dining", "restaurant", "restaurants", "eating out",
               "swiggy", "zomato", "food delivery", "dining out"],
    "membership": ["membership", "club membership", "golf club"],
    # gym lives here, not in healthcare — fitness spend is lifestyle
    "gym": ["gym", "gym membership", "fitness center", "fitness centre",
            "cult fit", "cultfit", "workout", "home workout",
            "home gym", "fitness subscription"],
}


def build_reverse_map() -> dict[str, str]:
    """Build a synonym → canonical lookup.

    Lowercases everything. If a phrase appears under two canonicals (which
    shouldn't happen, but guards against editor error), the last-written
    canonical wins — deterministic by dict insertion order.
    """
    reverse: dict[str, str] = {}
    for canonical, phrases in SYNONYMS.items():
        for phrase in phrases:
            reverse[phrase.lower().strip()] = canonical
    return reverse


# Precomputed once at import time.
REVERSE_SYNONYMS: dict[str, str] = build_reverse_map()
