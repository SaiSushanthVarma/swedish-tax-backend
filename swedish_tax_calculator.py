import re

# 1. COMPLETE 2026 MUNICIPALITY TAX RATES (from SCB official data)

KOMMUNAL_SKATT_2026 = {
    "ale": 32.80, "alingsås": 32.84, "alvesta": 33.42, "aneby": 33.85,
    "arboga": 33.29, "arjeplog": 34.84, "arvidsjaur": 34.14, "arvika": 34.03,
    "askersund": 34.15, "avesta": 33.95, "bengtsfors": 34.40, "berg": 34.22,
    "bjurholm": 35.00, "bjuv": 32.17, "boden": 33.94, "bollebygd": 33.07,
    "bollnäs": 33.37, "borgholm": 33.44, "borlänge": 34.40, "borås": 32.79,
    "botkyrka": 32.23, "boxholm": 33.37, "bromölla": 33.74, "bräcke": 35.09,
    "burlöv": 31.27, "båstad": 31.41, "dals-ed": 34.69, "danderyd": 30.58,
    "degerfors": 35.30, "dorotea": 35.65, "eda": 34.55, "ekerö": 31.45,
    "eksjö": 34.02, "emmaboda": 33.82, "enköping": 33.05, "eskilstuna": 32.85,
    "eslöv": 31.72, "essunga": 33.05, "fagersta": 32.99, "falkenberg": 32.50,
    "falköping": 33.43, "falun": 34.05, "filipstad": 34.55, "finspång": 33.70,
    "flen": 33.10, "forshaga": 34.63, "färgelanda": 34.39, "gagnef": 34.27,
    "gislaved": 33.75, "gnesta": 32.95, "gnosjö": 34.00, "gotland": 33.60,
    "grums": 34.78, "grästorp": 33.47, "gullspång": 33.97, "gällivare": 33.89,
    "gävle": 33.77, "göteborg": 32.60, "götene": 33.60, "habo": 33.93,
    "hagfors": 34.30, "hallsberg": 33.85, "hallstahammar": 32.69, "halmstad": 32.38,
    "hammarö": 35.05, "haninge": 31.28, "haparanda": 33.84, "heby": 34.21,
    "hedemora": 34.15, "helsingborg": 31.39, "herrljunga": 33.62, "hjo": 33.48,
    "hofors": 34.37, "huddinge": 31.71, "hudiksvall": 33.12, "hultsfred": 33.77,
    "hylte": 33.85, "håbo": 33.30, "hällefors": 34.35, "härjedalen": 34.17,
    "härnösand": 34.63, "härryda": 31.98, "hässleholm": 32.38, "höganäs": 30.91,
    "högsby": 34.07, "hörby": 32.26, "höör": 32.63, "jokkmokk": 34.29,
    "järfälla": 31.52, "jönköping": 33.40, "kalix": 33.89, "kalmar": 33.67,
    "karlsborg": 32.80, "karlshamn": 33.80, "karlskoga": 34.30, "karlskrona": 33.69,
    "karlstad": 33.55, "katrineholm": 32.95, "kil": 34.63, "kinda": 33.00,
    "kiruna": 34.39, "klippan": 31.93, "knivsta": 32.62, "kramfors": 34.43,
    "kristianstad": 32.64, "kristinehamn": 34.25, "krokom": 33.87, "kumla": 33.84,
    "kungsbacka": 32.58, "kungsör": 32.91, "kungälv": 32.92, "kävlinge": 29.59,
    "köping": 33.04, "laholm": 32.80, "landskrona": 31.42, "laxå": 35.00,
    "lekeberg": 33.73, "leksand": 33.80, "lerum": 32.03, "lessebo": 33.81,
    "lidingö": 29.67, "lidköping": 32.74, "lilla edet": 33.85, "lindesberg": 34.60,
    "linköping": 31.75, "ljungby": 33.07, "ljusdal": 33.87, "ljusnarsberg": 33.80,
    "lomma": 30.72, "ludvika": 34.05, "luleå": 33.84, "lund": 32.42,
    "lycksele": 34.90, "lysekil": 33.94, "malmö": 32.42, "malung-sälen": 34.45,
    "malå": 35.20, "mariestad": 32.74, "mark": 32.99, "markaryd": 33.31,
    "mellerud": 34.08, "mjölby": 33.45, "mora": 34.32, "motala": 33.25,
    "mullsjö": 34.10, "munkedal": 34.86, "munkfors": 34.30, "mölndal": 31.99,
    "mönsterås": 34.07, "mörbylånga": 34.07, "nacka": 30.11, "nora": 34.55,
    "norberg": 33.54, "nordanstig": 34.02, "nordmaling": 35.10, "norrköping": 33.30,
    "norrtälje": 32.05, "norsjö": 35.20, "nybro": 34.19, "nykvarn": 32.30,
    "nyköping": 32.25, "nynäshamn": 32.18, "nässjö": 34.30, "ockelbo": 34.27,
    "olofström": 33.75, "orsa": 34.30, "orust": 33.69, "osby": 33.99,
    "oskarshamn": 34.21, "ovanåker": 33.37, "oxelösund": 33.05, "pajala": 34.74,
    "partille": 31.36, "perstorp": 31.99, "piteå": 33.59, "ragunda": 34.92,
    "robertsfors": 35.00, "ronneby": 33.68, "rättvik": 33.80, "sala": 33.19,
    "salem": 32.00, "sandviken": 33.12, "sigtuna": 31.83, "simrishamn": 31.69,
    "sjöbo": 32.10, "skara": 33.38, "skellefteå": 34.45, "skinnskatteberg": 33.34,
    "skurup": 31.60, "skövde": 33.09, "smedjebacken": 34.44, "sollefteå": 34.68,
    "sollentuna": 30.45, "solna": 29.70, "sorsele": 35.45, "sotenäs": 33.47,
    "staffanstorp": 30.12, "stenungsund": 33.12, "stockholm": 30.55, "storfors": 34.98,
    "storuman": 34.95, "strängnäs": 32.50, "strömstad": 33.39, "strömsund": 34.92,
    "sundbyberg": 31.58, "sundsvall": 33.88, "sunne": 33.75, "surahammar": 33.19,
    "svalöv": 31.92, "svedala": 31.42, "svenljunga": 33.53, "säffle": 33.80,
    "säter": 34.30, "sävsjö": 33.68, "söderhamn": 33.17, "söderköping": 33.53,
    "södertälje": 32.38, "sölvesborg": 33.86, "tanum": 33.04, "tibro": 33.19,
    "tidaholm": 33.55, "tierp": 33.00, "timrå": 34.38, "tingsryd": 34.00,
    "tjörn": 33.19, "tomelilla": 31.79, "torsby": 34.30, "torsås": 33.79,
    "tranemo": 32.98, "tranås": 33.77, "trelleborg": 31.58, "trollhättan": 33.84,
    "trosa": 32.03, "tyresö": 31.83, "täby": 29.88, "töreboda": 33.20,
    "uddevalla": 33.64, "ulricehamn": 32.53, "umeå": 34.65, "upplands väsby": 31.75,
    "upplands-bro": 31.73, "uppsala": 32.85, "uppvidinge": 33.80, "vadstena": 34.35,
    "vaggeryd": 33.25, "valdemarsvik": 34.03, "vallentuna": 31.23, "vansbro": 34.28,
    "vara": 33.25, "varberg": 31.73, "vaxholm": 31.63, "vellinge": 29.68,
    "vetlanda": 33.77, "vilhelmina": 35.50, "vimmerby": 34.22, "vindeln": 35.20,
    "vingåker": 33.50, "vårgårda": 33.09, "vänersborg": 33.69, "vännäs": 35.20,
    "värmdö": 31.31, "värnamo": 33.28, "västervik": 33.02, "västerås": 31.24,
    "växjö": 32.19, "ydre": 34.10, "ystad": 31.29, "åmål": 33.94,
    "ånge": 34.62, "åre": 33.92, "årjäng": 34.25, "åsele": 35.45,
    "åstorp": 31.47, "åtvidaberg": 33.94, "älmhult": 33.86, "älvdalen": 34.77,
    "älvkarleby": 34.40, "älvsbyn": 33.79, "ängelholm": 31.35, "öckerö": 33.04,
    "ödeshög": 33.95, "örebro": 33.65, "örkelljunga": 30.24, "örnsköldsvik": 33.85,
    "östersund": 33.72, "österåker": 28.93, "östhammar": 33.30, "östra göinge": 32.17,
    "överkalix": 34.14, "övertorneå": 33.84,
}

# 2. TAX CALCULATION RULES 2026 (from Skatteverket)

STATE_TAX_THRESHOLD_2026 = 643000  # skiktgräns before grundavdrag
STATE_TAX_RATE = 0.20
PRISBASBELOPP_2026 = 59200


def calculate_grundavdrag(income: float) -> float:
    pbb = 59200  # prisbasbelopp 2026
    if income <= 0:
        return 0
    elif income <= 0.99 * pbb:
        return 0.423 * income
    elif income <= 2.72 * pbb:
        return 0.423 * 0.99 * pbb + 0.20 * (income - 0.99 * pbb)
    elif income <= 3.11 * pbb:
        return min(0.36 * pbb, 0.423 * 0.99 * pbb + 0.20 * (income - 0.99 * pbb))
    elif income <= 7.88 * pbb:
        return 0.36 * pbb
    elif income <= 10.0 * pbb:
        return 0.36 * pbb + 0.20 * (income - 7.88 * pbb)
    elif income <= 12.75 * pbb:
        return min(0.77 * pbb, 0.36 * pbb + 0.20 * (income - 7.88 * pbb))
    else:
        return max(0.17 * pbb, 0.77 * pbb - 0.20 * (income - 12.75 * pbb))


def calculate_jobbskatteavdrag(income: float, kommunal_rate: float) -> float:
    rate = kommunal_rate / 100
    if income <= 100000:
        jsa = income * rate * 0.3492
    elif income <= 300000:
        jsa = (100000 * rate * 0.3492) + ((income - 100000) * rate * 0.6831)
    elif income <= 600000:
        jsa = (100000 * rate * 0.3492) + (200000 * rate * 0.6831) + ((income - 300000) * rate * 0.5233)
    else:
        jsa = (100000 * rate * 0.3492) + (200000 * rate * 0.6831) + (300000 * rate * 0.5233)
        jsa = max(0, jsa - (income - 600000) * rate * 0.03)
    return min(jsa, 50000)


# 3. MAIN CALCULATION FUNCTION

def calculate_tax(salary: float, kommun: str) -> dict:
    """
    Calculate Swedish income tax for employed person.
    Source: Skatteverket 2026 rules + SCB municipality rates.
    """
    kommun_lower = kommun.lower().strip()

    kommunal_rate = None
    matched_kommun = None

    if kommun_lower in KOMMUNAL_SKATT_2026:
        kommunal_rate = KOMMUNAL_SKATT_2026[kommun_lower]
        matched_kommun = kommun.title()
    else:
        for k, v in KOMMUNAL_SKATT_2026.items():
            if kommun_lower in k or k in kommun_lower:
                kommunal_rate = v
                matched_kommun = k.title()
                break

    if kommunal_rate is None:
        kommunal_rate = 32.38
        matched_kommun = f"{kommun.title()} (using national average)"

    grundavdrag = calculate_grundavdrag(salary)
    taxable_income = max(0, salary - grundavdrag)
    kommunal_skatt = taxable_income * (kommunal_rate / 100)

    statlig_skatt = 0
    if taxable_income > STATE_TAX_THRESHOLD_2026:
        statlig_skatt = (taxable_income - STATE_TAX_THRESHOLD_2026) * STATE_TAX_RATE

    jsa = calculate_jobbskatteavdrag(salary, kommunal_rate)
    total_tax_before_jsa = kommunal_skatt + statlig_skatt
    total_tax = max(0, total_tax_before_jsa - jsa)

    net_salary_year = salary - total_tax
    net_salary_month = net_salary_year / 12
    effective_rate = (total_tax / salary * 100) if salary > 0 else 0

    return {
        "salary": salary,
        "kommun": matched_kommun,
        "kommunal_rate": kommunal_rate,
        "grundavdrag": round(grundavdrag),
        "taxable_income": round(taxable_income),
        "kommunal_skatt": round(kommunal_skatt),
        "statlig_skatt": round(statlig_skatt),
        "jobbskatteavdrag": round(jsa),
        "total_tax": round(total_tax),
        "net_salary_year": round(net_salary_year),
        "net_salary_month": round(net_salary_month),
        "effective_rate": round(effective_rate, 1),
        "state_tax_applies": taxable_income > STATE_TAX_THRESHOLD_2026,
        "data_source": "SCB 2026 + Skatteverket rules",
    }


# 4. DETECT CALCULATION REQUESTS

def detect_calculation_request(question: str) -> dict:
    """Detect if user is asking for a tax calculation with salary + location."""

    question_lower = question.lower()

    monthly_patterns = [
        r'(\d[\d\s,]+)\s*(?:kr|sek)?\s*(?:per|a|/)\s*(?:month|månad|mån)',
        r'(?:monthly|månads(?:lön)?)[:\s]+(\d[\d\s,]+)',
        r'(\d[\d\s,]+)\s*kr\s*(?:i månaden|per månaden)',
        r'(\d{4,6})\s*(?:kr\s*)?monthly',
        r'(\d{4,6})\s*(?:kr\s*)?(?:per|a)\s*month',
    ]

    monthly_salary = None
    for pattern in monthly_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(' ', '').replace(',', '')
            try:
                val = float(raw)
                if 5000 <= val <= 200000:
                    monthly_salary = val * 12
                    print(f"Monthly salary detected: {val}/month = {monthly_salary}/year")
                    break
            except Exception:
                pass

    salary = monthly_salary

    # Yearly salary detection — only runs if monthly detection found nothing
    if salary is None:
        yearly_patterns = [
            r'(\d[\d\s]*[\d])\s*(?:kr|sek|kronor)',
            r'(\d+)\s*(?:tusen|thousand)',
            r'salary\s+(?:of\s+)?(\d[\d\s,]*)',
            r'lön\s+(?:på\s+)?(\d[\d\s]*)',
            r'tjänar\s+(\d[\d\s]*)',
            r'earn\s+(\d[\d\s,]*)',
        ]
        for pattern in yearly_patterns:
            match = re.search(pattern, question_lower)
            if match:
                raw = match.group(1).replace(' ', '').replace(',', '')
                try:
                    val = float(raw)
                    if val < 1000 and 'tusen' in question_lower:
                        val *= 1000
                    elif val >= 100:
                        salary = val
                    break
                except Exception:
                    pass

    kommun = None
    # Sort by length descending so longer names match first
    # (avoids "ale" matching inside "alingsås")
    sorted_kommuner = sorted(KOMMUNAL_SKATT_2026.keys(), key=len, reverse=True)

    for k in sorted_kommuner:
        # Use word boundary matching to avoid partial matches
        # e.g. "sala" should not match inside "salary"
        pattern = r'\b' + re.escape(k) + r'\b'
        if re.search(pattern, question_lower):
            kommun = k
            break

    city_aliases = {
        "orebro": "örebro",
        "goteborg": "göteborg",
        "gothenburg": "göteborg",
        "malmo": "malmö",
        "vasteras": "västerås",
        "linkoping": "linköping",
        "norrkoping": "norrköping",
        "jonkoping": "jönköping",
        "umea": "umeå",
        "gavle": "gävle",
        "lulea": "luleå",
        "ostersund": "östersund",
        "ornskoldsvik": "örnsköldsvik",
        "sundsvall": "sundsvall",
        "borlange": "borlänge",
        "falun": "falun",
        "karlstad": "karlstad",
        "eskilstuna": "eskilstuna",
        "vaxjo": "växjö",
        "helsingborg": "helsingborg",
        "stockholm": "stockholm",
    }
    if not kommun:
        for alias, real in city_aliases.items():
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, question_lower):
                kommun = real
                break

    needs_calculation = salary is not None and (
        'tax' in question_lower or 'skatt' in question_lower or
        'calculate' in question_lower or 'räkna' in question_lower or
        'net' in question_lower or 'netto' in question_lower or
        'take home' in question_lower or 'hand' in question_lower or
        'salary' in question_lower or 'lön' in question_lower or
        'income' in question_lower or 'inkomst' in question_lower
    )

    return {
        "needs_calculation": needs_calculation,
        "salary": salary,
        "kommun": kommun or "sverige",
    }


if __name__ == "__main__":
    result = calculate_tax(700000, "örebro")
    print(f"\n=== Tax Calculation for {result['kommun']} ===")
    print(f"Gross salary:        {result['salary']:>12,.0f} kr/year")
    print(f"Basic deduction:   - {result['grundavdrag']:>12,.0f} kr")
    print(f"Taxable income:      {result['taxable_income']:>12,.0f} kr")
    print(f"Municipal tax {result['kommunal_rate']}%: - {result['kommunal_skatt']:>12,.0f} kr")
    print(f"State tax:         - {result['statlig_skatt']:>12,.0f} kr")
    print(f"Jobbskatteavdrag:  + {result['jobbskatteavdrag']:>12,.0f} kr")
    print(f"Total tax:           {result['total_tax']:>12,.0f} kr")
    print(f"NET/year:            {result['net_salary_year']:>12,.0f} kr")
    print(f"NET/month:           {result['net_salary_month']:>12,.0f} kr")
    print(f"Effective rate:      {result['effective_rate']:>11.1f} %")

    test_questions = [
        "My salary is 700000 kr in Örebro, what is my tax?",
        "Jag tjänar 500000 kr i Stockholm, vad får jag netto?",
        "Calculate tax for 45000 kr salary in Malmö",
    ]
    print("\n=== Detection Tests ===")
    for q in test_questions:
        r = detect_calculation_request(q)
        print(f"Q: {q[:50]}")
        print(f"   → needs_calc={r['needs_calculation']}, salary={r['salary']}, kommun={r['kommun']}\n")
