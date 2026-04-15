FACTS_2026 = {
    "state_tax_threshold": 643000,
    "state_tax_rate": 20,
    "national_average_kommunalskatt": 32.38,
    "prisbasbelopp": 59200,
    "grundavdrag_max": 47100,
    "arbetsgivaravgift": 31.42,
    "moms_standard": 25,
    "moms_food": 12,
    "moms_transport": 6,
    "rot_deduction": 30,
    "rut_deduction": 50,
    "rot_max_per_person": 50000,
    "rut_max_per_person": 75000,
    "isk_schablonrate_2026": 1.086,
    "capital_gains_tax": 30,
    "pension_contribution": 7,
    # Reseavdrag 2026
    "reseavdrag_rate_own_car": 2.50,
    "reseavdrag_rate_company_car_fuel": 1.20,
    "reseavdrag_rate_company_car_electric": 0.95,
    "reseavdrag_threshold_2026": 15000,
    "reseavdrag_threshold_2025": 11000,
    "reseavdrag_min_distance_km": 5,
    "reseavdrag_min_time_saving_hours": 2,
    "year": 2026,
    "source": "Skatteverket + SCB 2026",
}

QUICK_ANSWERS = {
    "moms": "Standard VAT (moms) in Sweden is 25%. Food is 12%, transport and books are 6%.",
    "statlig skatt": "State tax (statlig inkomstskatt) is 20% on taxable income above 643,000 kr (2026).",
    "arbetsgivaravgift": "Employer contributions (arbetsgivaravgifter) are 31.42% on top of gross salary.",
    "rot": "ROT deduction covers 30% of labor costs for home repairs, max 50,000 kr per person per year.",
    "rut": "RUT deduction covers 50% of labor costs for cleaning/household services, max 75,000 kr per year.",
    "isk": "ISK (Investeringssparkonto) is taxed at 1.086% of account value annually (2026 schablon rate).",
    "kapitalvinstskatt": "Capital gains tax in Sweden is 30% flat rate.",
    "pension": "You pay 7% of your salary (up to a ceiling) as pension contribution.",
    "reseavdrag": """Reseavdrag 2026 rules (own car):
- Rate: 25 kr/mil = 2.50 kr/km (flat rate, all fuel types)
- Minimum distance: 5 km one way
- Must save at least 2 hours/day vs public transport
- Threshold: Only costs ABOVE 15,000 kr/year are deductible
  (Note: for income year 2025 declared in 2026, threshold is still 11,000 kr)
  (For income year 2026 declared in 2027, threshold rises to 15,000 kr)
- File under: Ruta 2.1 in your Inkomstdeklaration
Source: Skatteverket 2026""",
    "km avdrag": """Car travel deduction rate Sweden 2026:
25 kr per mil = 2.50 kr per km for own car (flat rate).
Company car (petrol/diesel): 12 kr/mil = 1.20 kr/km
Company car (electric): 9.50 kr/mil = 0.95 kr/km
Source: Skatteverket 2026""",
    "milersättning": """Milersättning 2026:
Own car: 25 kr/mil (2.50 kr/km) — unchanged from 2025
Company car petrol/diesel: 12 kr/mil
Company car electric: 9.50 kr/mil
Source: Skatteverket 2026""",
}


def calculate_reseavdrag(km_one_way: float, work_days: int, year: int = 2026) -> dict:
    """Calculate commute tax deduction."""
    rate_per_km = 2.50  # 25 kr/mil
    threshold = 15000 if year >= 2026 else 11000

    total_km = km_one_way * 2 * work_days  # round trip x days
    total_cost = total_km * rate_per_km
    deductible = max(0, total_cost - threshold)
    tax_saving = deductible * 0.30  # approx 30% tax rate

    return {
        "km_one_way": km_one_way,
        "work_days": work_days,
        "total_km_year": total_km,
        "total_cost": round(total_cost),
        "threshold": threshold,
        "deductible_amount": round(deductible),
        "estimated_tax_saving": round(tax_saving),
        "qualifies": total_cost > threshold,
        "rate_per_km": rate_per_km,
        "year": year,
    }
