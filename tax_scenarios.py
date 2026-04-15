SCENARIOS = {
    "enskild_firma": {
        "name": "Enskild firma tax calculation",
        "steps": [
            "Calculate egenavgifter (28.97% for under 66)",
            "Calculate schablonavdrag (25% of profit)",
            "Apply expansionsfond if applicable",
            "Calculate final income tax",
        ],
        "formula": lambda profit, kommunal_rate: {
            "egenavgifter": profit * 0.2897,
            "schablonavdrag": profit * 0.25 * 0.2897,
        },
    },
    "rotavdrag": {
        "name": "ROT deduction calculator",
        "formula": lambda labor_cost: {
            "deduction": min(labor_cost * 0.30, 50000),
            "you_pay": labor_cost - min(labor_cost * 0.30, 50000),
        },
    },
    "rutavdrag": {
        "name": "RUT deduction calculator",
        "formula": lambda labor_cost: {
            "deduction": min(labor_cost * 0.50, 75000),
            "you_pay": labor_cost - min(labor_cost * 0.50, 75000),
        },
    },
    "reseavdrag": {
        "name": "Commute deduction calculator",
        # Must be > 11 km one way AND savings > 2,000 kr vs public transport
        # 0.25 kr/km above 11 km each way, minus threshold of 11,000 kr
        "formula": lambda km, days: {
            "deduction": max(0, (km * 2 - 11) * days * 0.25 - 11000),
        },
    },
}
