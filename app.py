"""
CarbonWise — Personal Carbon Footprint Tracker
A terminal-based app to understand, track, and reduce your carbon footprint.
"""

import json
import os
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import math

# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class Activity:
    """A single carbon-emitting activity logged by the user."""
    date: str
    category: str
    subcategory: str
    amount: float          # raw input (km, kWh, kg, etc.)
    unit: str
    co2_kg: float          # calculated CO2 in kg
    note: str = ""

@dataclass
class UserProfile:
    """Stores user preferences and cumulative data."""
    name: str = "User"
    country: str = "India"
    goal_kg_per_month: float = 200.0
    activities: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.date.today().isoformat())

# ─── Emission Factors (kg CO2 per unit) ─────────────────────────────────────

EMISSION_FACTORS = {
    "Transport": {
        "Car (petrol)":        {"factor": 0.21,  "unit": "km",    "emoji": "🚗"},
        "Car (diesel)":        {"factor": 0.17,  "unit": "km",    "emoji": "🚙"},
        "Car (electric)":      {"factor": 0.05,  "unit": "km",    "emoji": "⚡"},
        "Motorcycle":          {"factor": 0.11,  "unit": "km",    "emoji": "🏍️"},
        "Bus":                 {"factor": 0.089, "unit": "km",    "emoji": "🚌"},
        "Train / Metro":       {"factor": 0.041, "unit": "km",    "emoji": "🚆"},
        "Domestic flight":     {"factor": 0.255, "unit": "km",    "emoji": "✈️"},
        "International flight":{"factor": 0.195, "unit": "km",    "emoji": "🌍"},
        "Auto-rickshaw":       {"factor": 0.078, "unit": "km",    "emoji": "🛺"},
    },
    "Home Energy": {
        "Electricity (grid)":  {"factor": 0.716, "unit": "kWh",  "emoji": "💡"},
        "LPG cooking gas":     {"factor": 2.983, "unit": "kg",   "emoji": "🔥"},
        "Natural gas":         {"factor": 2.204, "unit": "m³",   "emoji": "🌡️"},
        "Firewood / biomass":  {"factor": 1.747, "unit": "kg",   "emoji": "🪵"},
    },
    "Food": {
        "Beef / mutton":       {"factor": 27.0,  "unit": "kg",   "emoji": "🥩"},
        "Chicken / poultry":   {"factor": 6.9,   "unit": "kg",   "emoji": "🍗"},
        "Fish / seafood":      {"factor": 6.1,   "unit": "kg",   "emoji": "🐟"},
        "Dairy (milk/paneer)": {"factor": 3.2,   "unit": "kg",   "emoji": "🥛"},
        "Eggs":                {"factor": 4.5,   "unit": "dozen","emoji": "🥚"},
        "Rice":                {"factor": 2.7,   "unit": "kg",   "emoji": "🍚"},
        "Vegetables / fruits": {"factor": 0.4,   "unit": "kg",   "emoji": "🥦"},
        "Restaurant meal":     {"factor": 2.5,   "unit": "meals","emoji": "🍽️"},
    },
    "Shopping": {
        "Clothing / textiles": {"factor": 20.0,  "unit": "item", "emoji": "👕"},
        "Electronics":         {"factor": 300.0, "unit": "item", "emoji": "📱"},
        "Furniture":           {"factor": 50.0,  "unit": "item", "emoji": "🪑"},
        "Online parcel":       {"factor": 0.5,   "unit": "parcel","emoji":"📦"},
        "Plastic items":       {"factor": 6.0,   "unit": "kg",   "emoji": "🛍️"},
    },
    "Waste": {
        "Landfill waste":      {"factor": 0.57,  "unit": "kg",   "emoji": "🗑️"},
        "Recycled waste":      {"factor": 0.02,  "unit": "kg",   "emoji": "♻️"},
        "Composted waste":     {"factor": 0.01,  "unit": "kg",   "emoji": "🌱"},
    },
}

CATEGORY_COLORS = {
    "Transport":   "\033[94m",   # blue
    "Home Energy": "\033[93m",   # yellow
    "Food":        "\033[92m",   # green
    "Shopping":    "\033[95m",   # magenta
    "Waste":       "\033[96m",   # cyan
}

# ─── Terminal Colors ─────────────────────────────────────────────────────────

C = {
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "blue":   "\033[94m",
    "cyan":   "\033[96m",
    "white":  "\033[97m",
    "gray":   "\033[90m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
    "dim":    "\033[2m",
    "bg_green": "\033[42m",
    "bg_red":   "\033[41m",
}

def clr(text: str, *codes) -> str:
    return "".join(C[c] for c in codes) + str(text) + C["reset"]

# ─── Storage ─────────────────────────────────────────────────────────────────

DATA_FILE = os.path.expanduser("~/.carbonwise_data.json")

def save_profile(profile: UserProfile):
    with open(DATA_FILE, "w") as f:
        json.dump(asdict(profile), f, indent=2)

def load_profile() -> UserProfile:
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
        profile = UserProfile(
            name=data.get("name", "User"),
            country=data.get("country", "India"),
            goal_kg_per_month=data.get("goal_kg_per_month", 200.0),
            activities=[Activity(**a) for a in data.get("activities", [])],
            created_at=data.get("created_at", datetime.date.today().isoformat()),
        )
        return profile
    except Exception:
        return None

# ─── UI Helpers ──────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print(clr("""
╔══════════════════════════════════════════════════════════╗
║         🌿  C A R B O N W I S E  🌿                     ║
║         Personal Carbon Footprint Tracker                ║
╚══════════════════════════════════════════════════════════╝""", "green", "bold"))

def divider(char="─", width=60, color="gray"):
    print(clr(char * width, color))

def prompt(msg: str, default=None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"  {clr('▶', 'cyan')} {msg}{clr(suffix, 'gray')}: ").strip()
    return val if val else (str(default) if default is not None else "")

def success(msg): print(f"\n  {clr('✓', 'green', 'bold')} {msg}")
def warn(msg):    print(f"\n  {clr('⚠', 'yellow', 'bold')} {msg}")
def error(msg):   print(f"\n  {clr('✗', 'red', 'bold')} {msg}")
def info(msg):    print(f"  {clr('ℹ', 'cyan')} {msg}")

def co2_bar(kg: float, max_kg: float = 50, width: int = 30) -> str:
    """Render a compact ASCII bar for CO2 amount."""
    pct = min(kg / max_kg, 1.0)
    filled = math.ceil(pct * width)
    if pct < 0.4:    bar_color = "green"
    elif pct < 0.75: bar_color = "yellow"
    else:            bar_color = "red"
    bar = clr("█" * filled, bar_color) + clr("░" * (width - filled), "gray")
    return f"[{bar}]"

def trend_arrow(current: float, previous: float) -> str:
    if previous == 0:
        return clr("  NEW", "cyan")
    pct = ((current - previous) / previous) * 100
    if pct <= -5:
        return clr(f"↓ {abs(pct):.0f}%", "green", "bold")
    elif pct >= 5:
        return clr(f"↑ {pct:.0f}%", "red", "bold")
    else:
        return clr(f"→ {pct:+.0f}%", "yellow")

# ─── Core Logic ──────────────────────────────────────────────────────────────

def calculate_co2(subcategory: str, amount: float) -> float:
    for cat_data in EMISSION_FACTORS.values():
        if subcategory in cat_data:
            return round(cat_data[subcategory]["factor"] * amount, 4)
    return 0.0

def get_monthly_totals(profile: UserProfile) -> dict:
    """Returns {YYYY-MM: total_kg} for all months."""
    totals = {}
    for a in profile.activities:
        month = a.date[:7]
        totals[month] = totals.get(month, 0.0) + a.co2_kg
    return totals

def get_this_month_total(profile: UserProfile) -> float:
    this_month = datetime.date.today().strftime("%Y-%m")
    return sum(a.co2_kg for a in profile.activities if a.date.startswith(this_month))

def get_category_breakdown(profile: UserProfile, month: Optional[str] = None) -> dict:
    breakdown = {}
    for a in profile.activities:
        if month and not a.date.startswith(month):
            continue
        breakdown[a.category] = breakdown.get(a.category, 0.0) + a.co2_kg
    return breakdown

# ─── Screens ─────────────────────────────────────────────────────────────────

def screen_onboarding() -> UserProfile:
    clear()
    banner()
    print(clr("\n  Welcome! Let's set up your profile.\n", "white"))
    name    = prompt("Your name", "EcoUser")
    country = prompt("Country", "India")
    goal    = prompt("Monthly CO₂ goal (kg) — global avg is ~833 kg/person", "300")
    try:
        goal_f = float(goal)
    except ValueError:
        goal_f = 300.0
    profile = UserProfile(name=name, country=country, goal_kg_per_month=goal_f)
    save_profile(profile)
    success(f"Profile created! Let's track your footprint, {name}.")
    input(clr("\n  Press Enter to continue…", "gray"))
    return profile

def screen_dashboard(profile: UserProfile):
    clear()
    banner()
    today = datetime.date.today()
    this_month = today.strftime("%Y-%m")
    month_label = today.strftime("%B %Y")

    total_this_month = get_this_month_total(profile)
    goal             = profile.goal_kg_per_month
    pct_used         = (total_this_month / goal * 100) if goal else 0

    monthly_totals = get_monthly_totals(profile)
    months_sorted  = sorted(monthly_totals.keys())
    last_month     = monthly_totals.get(
        (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m"), 0.0
    )

    print(f"\n  {clr('Hello,', 'gray')} {clr(profile.name, 'white', 'bold')}  "
          f"{clr('·', 'gray')}  {clr(today.strftime('%d %b %Y'), 'gray')}\n")
    divider()

    # ── Monthly Summary ──
    color = "green" if pct_used <= 70 else ("yellow" if pct_used <= 100 else "red")
    print(f"\n  {clr('THIS MONTH', 'gray', 'bold')}   {clr(month_label, 'white')}")
    print(f"\n  {clr(f'{total_this_month:.1f}', color, 'bold')} kg CO₂  "
          f"{clr('/', 'gray')}  {clr(f'{goal:.0f}', 'gray')} kg goal  "
          f"  {trend_arrow(total_this_month, last_month)}\n")
    print(f"  {co2_bar(total_this_month, max_kg=goal)}  {clr(f'{pct_used:.0f}%', color)}\n")

    if pct_used > 100:
        warn(f"You've exceeded your monthly goal by {total_this_month - goal:.1f} kg!")
    elif pct_used > 75:
        warn(f"Only {goal - total_this_month:.1f} kg remaining this month.")
    elif pct_used < 40:
        success("You're well within your monthly goal. Keep it up! 🌱")

    divider()

    # ── Category Breakdown ──
    breakdown = get_category_breakdown(profile, this_month)
    if breakdown:
        print(f"\n  {clr('BREAKDOWN BY CATEGORY', 'gray', 'bold')}\n")
        for cat, kg in sorted(breakdown.items(), key=lambda x: -x[1]):
            cat_color = CATEGORY_COLORS.get(cat, "\033[97m")
            bar       = co2_bar(kg, max_kg=max(breakdown.values()), width=20)
            print(f"  {cat_color}{cat:<18}\033[0m  {bar}  "
                  f"{clr(f'{kg:.1f} kg', 'white')}")
        print()
    else:
        print(f"\n  {clr('No activities logged this month yet.', 'gray')}\n")

    # ── Mini History ──
    if len(months_sorted) > 1:
        divider()
        print(f"\n  {clr('MONTHLY HISTORY', 'gray', 'bold')}\n")
        for m in months_sorted[-5:]:
            kg      = monthly_totals[m]
            bar     = co2_bar(kg, max_kg=goal, width=20)
            marker  = clr(" ◀ this month", "cyan") if m == this_month else ""
            print(f"  {clr(m, 'gray')}  {bar}  {clr(f'{kg:.1f} kg', 'white')}{marker}")
        print()

    divider()
    print(f"\n  {clr('Total activities logged:', 'gray')} {len(profile.activities)}")
    print(f"  {clr('Account since:', 'gray')} {profile.created_at}\n")

def screen_log_activity(profile: UserProfile):
    clear()
    banner()
    print(clr("\n  Log a New Activity\n", "white", "bold"))

    # Step 1: Choose category
    categories = list(EMISSION_FACTORS.keys())
    print(f"  {clr('Select a category:', 'gray')}\n")
    for i, cat in enumerate(categories, 1):
        cat_color = CATEGORY_COLORS.get(cat, "\033[97m")
        print(f"  {clr(str(i), 'cyan')}  {cat_color}{cat}\033[0m")
    print()
    cat_choice = prompt("Category number")
    try:
        category = categories[int(cat_choice) - 1]
    except (ValueError, IndexError):
        error("Invalid selection.")
        input(clr("\n  Press Enter…", "gray"))
        return

    # Step 2: Choose subcategory
    print(f"\n  {clr(f'Activities in {category}:', 'gray')}\n")
    subcat_list = list(EMISSION_FACTORS[category].items())
    for i, (name, meta) in enumerate(subcat_list, 1):
        unit_label = meta['unit']
        print(f"  {clr(str(i), 'cyan')}  {meta['emoji']}  {name:<28} "
              f"{clr(f'per {unit_label}', 'gray')}")
    print()
    sub_choice = prompt("Activity number")
    try:
        subcategory, meta = subcat_list[int(sub_choice) - 1]
    except (ValueError, IndexError):
        error("Invalid selection.")
        input(clr("\n  Press Enter…", "gray"))
        return

    # Step 3: Enter amount
    unit_str = meta['unit']
    print(f"\n  {clr(f'How many {unit_str}?', 'gray')}  "
          f"{clr(f'(e.g. 15 {unit_str} of {subcategory})', 'dim')}")
    unit_str2 = meta['unit']
    amount_str = prompt(f"Amount in {unit_str2}")
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        error("Please enter a positive number.")
        input(clr("\n  Press Enter…", "gray"))
        return

    # Step 4: Date
    today_str = datetime.date.today().isoformat()
    date_str  = prompt("Date (YYYY-MM-DD)", today_str)
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        date_str = today_str

    # Step 5: Optional note
    note = prompt("Note (optional)", "")

    # Calculate
    co2_kg = calculate_co2(subcategory, amount)
    activity = Activity(
        date=date_str,
        category=category,
        subcategory=subcategory,
        amount=amount,
        unit=meta["unit"],
        co2_kg=co2_kg,
        note=note,
    )
    profile.activities.append(activity)
    save_profile(profile)

    print(f"\n  {clr('Activity logged!', 'green', 'bold')}\n")
    print(f"  {meta['emoji']}  {clr(subcategory, 'white')}  ·  "
          f"{clr(str(amount) + ' ' + meta['unit'], 'gray')}")
    print(f"\n  {clr('CO₂ emitted:', 'gray')} {clr(f'{co2_kg:.2f} kg', 'yellow', 'bold')}\n")
    print(f"  {co2_bar(co2_kg, max_kg=20)}")
    _show_co2_context(co2_kg)
    input(clr("\n\n  Press Enter to continue…", "gray"))

def _show_co2_context(co2_kg: float):
    """Give a real-world comparison for the CO₂ amount."""
    comparisons = [
        (0.5,  "charging a smartphone ~60 times"),
        (2.0,  "streaming 3 hours of HD video"),
        (5.0,  "producing 1 kg of chicken"),
        (10.0, "driving ~50 km in a petrol car"),
        (27.0, "producing 1 kg of beef"),
        (50.0, "a one-way domestic flight"),
    ]
    closest = min(comparisons, key=lambda x: abs(co2_kg - x[0]))
    equiv_n = co2_kg / closest[0]
    print(f"\n  {clr('≈', 'cyan')} That's equivalent to {clr(f'{equiv_n:.1f}×', 'yellow')} "
          f"{closest[1]}")

def screen_insights(profile: UserProfile):
    clear()
    banner()
    print(clr("\n  Personalised Insights & Recommendations\n", "white", "bold"))

    if not profile.activities:
        warn("Log some activities first to get personalised insights.")
        input(clr("\n  Press Enter…", "gray"))
        return

    this_month  = datetime.date.today().strftime("%Y-%m")
    breakdown   = get_category_breakdown(profile, this_month)
    total       = sum(breakdown.values())
    monthly_avg = 833.0  # global avg kg CO₂/person/month

    divider()
    print(f"\n  {clr('YOUR BIGGEST IMPACT AREAS', 'gray', 'bold')}\n")
    sorted_cats = sorted(breakdown.items(), key=lambda x: -x[1])
    for cat, kg in sorted_cats:
        pct = (kg / total * 100) if total else 0
        cat_color = CATEGORY_COLORS.get(cat, "\033[97m")
        print(f"  {cat_color}{cat:<18}\033[0m  {clr(f'{pct:.0f}%', 'white', 'bold')}  "
              f"{clr(f'of your footprint', 'gray')}")

    divider()
    print(f"\n  {clr('HOW YOU COMPARE', 'gray', 'bold')}\n")
    india_avg = 140.0   # kg CO₂/person/month (India)
    print(f"  {'You':>12}  {clr(f'{total:.1f} kg', 'white', 'bold')}")
    print(f"  {'India avg':>12}  {clr(f'{india_avg:.0f} kg', 'cyan')}")
    print(f"  {'Global avg':>12}  {clr(f'{monthly_avg:.0f} kg', 'yellow')}")
    print(f"  {'Goal':>12}  {clr(f'{profile.goal_kg_per_month:.0f} kg', 'green')}")

    divider()
    print(f"\n  {clr('ACTIONABLE TIPS FOR YOU', 'gray', 'bold')}\n")
    tips = _generate_tips(breakdown, profile)
    for i, tip in enumerate(tips, 1):
        print(f"  {clr(str(i), 'cyan', 'bold')}  {tip}\n")

    divider()
    # Quick wins
    print(f"\n  {clr('QUICK WINS', 'gray', 'bold')}\n")
    quick_wins = [
        ("🚶", "Walk / cycle trips under 3 km instead of riding",         "saves ~3 kg CO₂/week"),
        ("🌱", "Swap one red-meat meal for legumes / tofu per week",       "saves ~10 kg CO₂/month"),
        ("💡", "Switch to LED bulbs and unplug idle electronics",          "saves ~8 kg CO₂/month"),
        ("♻️", "Segregate waste for recycling / composting",               "saves ~5 kg CO₂/month"),
        ("🛒", "Buy second-hand clothing instead of new",                  "saves ~20 kg CO₂/item"),
    ]
    for emoji, action, saving in quick_wins:
        print(f"  {emoji}  {clr(action, 'white')}  {clr(f'→ {saving}', 'green')}")
    print()

    input(clr("  Press Enter to return…", "gray"))

def _generate_tips(breakdown: dict, profile: UserProfile) -> list:
    tips = []
    total = sum(breakdown.values()) or 1

    transport_pct  = breakdown.get("Transport", 0) / total
    energy_pct     = breakdown.get("Home Energy", 0) / total
    food_pct       = breakdown.get("Food", 0) / total
    shopping_pct   = breakdown.get("Shopping", 0) / total

    if transport_pct > 0.3:
        tips.append("🚗 Transport is your biggest emitter. Try public transport "
                    "or carpooling — even 2 days/week cuts this by ~40%.")
    if energy_pct > 0.25:
        tips.append("⚡ Your home energy use is high. Set your AC to 26°C+, "
                    "use a solar water heater, and consider rooftop solar.")
    if food_pct > 0.3:
        tips.append("🥩 Food choices matter a lot. Reducing beef/mutton to once "
                    "a week can cut food emissions by up to 50%.")
    if shopping_pct > 0.2:
        tips.append("🛍️ Shopping contributes heavily. Try a 30-day no-buy "
                    "challenge on clothing — it's the second-most impactful action.")

    if not tips:
        tips.append("✨ Your footprint looks balanced across categories. "
                    "Focus on small consistent improvements in each area.")
    if profile.goal_kg_per_month < 200:
        tips.append("🏆 Ambitious goal! Track weekly to stay on course — "
                    "small daily actions compound quickly.")

    tips.append("🌳 Offset unavoidable emissions: planting 6 trees absorbs ~1 tonne CO₂/year.")
    return tips

def screen_history(profile: UserProfile):
    clear()
    banner()
    print(clr("\n  Activity Log\n", "white", "bold"))

    if not profile.activities:
        warn("No activities logged yet.")
        input(clr("\n  Press Enter…", "gray"))
        return

    # Show latest 20, most-recent first
    recent = sorted(profile.activities, key=lambda a: a.date, reverse=True)[:20]
    print(f"  {clr('DATE        CATEGORY        ACTIVITY                   CO₂', 'gray')}")
    divider("─", 70)
    for a in recent:
        cat_color = CATEGORY_COLORS.get(a.category, "\033[97m")
        co2_color = "green" if a.co2_kg < 5 else ("yellow" if a.co2_kg < 20 else "red")
        print(f"  {clr(a.date, 'gray')}  "
              f"{cat_color}{a.category:<15}\033[0m  "
              f"{a.subcategory:<27}"
              f"{clr(f'{a.co2_kg:.2f} kg', co2_color)}")
    divider("─", 70)
    total = sum(a.co2_kg for a in profile.activities)
    print(f"  {clr('All-time total:', 'gray')} {clr(f'{total:.1f} kg CO₂', 'white', 'bold')}")
    print(f"  {clr('Showing latest 20 of', 'gray')} {len(profile.activities)} entries\n")

    input(clr("  Press Enter to return…", "gray"))

def screen_settings(profile: UserProfile):
    clear()
    banner()
    print(clr("\n  Settings\n", "white", "bold"))
    print(f"  {clr('Name:', 'gray')}          {profile.name}")
    print(f"  {clr('Country:', 'gray')}       {profile.country}")
    print(f"  {clr('Monthly goal:', 'gray')}  {profile.goal_kg_per_month} kg CO₂\n")
    divider()
    print(f"\n  {clr('1', 'cyan')}  Update name")
    print(f"  {clr('2', 'cyan')}  Update country")
    print(f"  {clr('3', 'cyan')}  Update monthly goal")
    print(f"  {clr('4', 'cyan')}  Delete all data  {clr('(irreversible)', 'red')}")
    print(f"  {clr('0', 'cyan')}  Back\n")

    choice = prompt("Choice")
    if choice == "1":
        profile.name = prompt("New name", profile.name)
        save_profile(profile)
        success("Name updated.")
    elif choice == "2":
        profile.country = prompt("New country", profile.country)
        save_profile(profile)
        success("Country updated.")
    elif choice == "3":
        try:
            profile.goal_kg_per_month = float(prompt("New goal (kg/month)", profile.goal_kg_per_month))
            save_profile(profile)
            success("Goal updated.")
        except ValueError:
            error("Invalid number.")
    elif choice == "4":
        confirm = prompt("Type 'DELETE' to confirm")
        if confirm == "DELETE":
            profile.activities = []
            save_profile(profile)
            success("All activity data deleted.")
        else:
            info("Cancelled.")
    input(clr("\n  Press Enter…", "gray"))

# ─── Main Loop ───────────────────────────────────────────────────────────────

def main():
    profile = load_profile()
    if not profile:
        profile = screen_onboarding()

    while True:
        screen_dashboard(profile)
        print(f"\n  {clr('MENU', 'gray', 'bold')}\n")
        print(f"  {clr('1', 'cyan')}  Log an activity")
        print(f"  {clr('2', 'cyan')}  View insights & tips")
        print(f"  {clr('3', 'cyan')}  Activity history")
        print(f"  {clr('4', 'cyan')}  Settings")
        print(f"  {clr('0', 'cyan')}  Exit\n")

        choice = prompt("Choose an option")
        if   choice == "1": screen_log_activity(profile)
        elif choice == "2": screen_insights(profile)
        elif choice == "3": screen_history(profile)
        elif choice == "4": screen_settings(profile)
        elif choice == "0":
            print(clr("\n  🌿 Keep making a difference. Goodbye!\n", "green"))
            break

if __name__ == "__main__":
    main()