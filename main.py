from fastapi import FastAPI
from datetime import datetime
import pytz
from lunar_python import Solar, Lunar
import datetime as dt

app = FastAPI()

STEM_INFO = {
    "甲": ("Wood", "Yang"),
    "乙": ("Wood", "Yin"),
    "丙": ("Fire", "Yang"),
    "丁": ("Fire", "Yin"),
    "戊": ("Earth", "Yang"),
    "己": ("Earth", "Yin"),
    "庚": ("Metal", "Yang"),
    "辛": ("Metal", "Yin"),
    "壬": ("Water", "Yang"),
    "癸": ("Water", "Yin")
}

GENERATES = {
    "Wood": "Fire",
    "Fire": "Earth",
    "Earth": "Metal",
    "Metal": "Water",
    "Water": "Wood"
}

CONTROLS = {
    "Wood": "Earth",
    "Earth": "Water",
    "Water": "Fire",
    "Fire": "Metal",
    "Metal": "Wood"
}

ALL_ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]

def build_chart(birth_date, birth_time, timezone, gender):
    tz = pytz.timezone(timezone)
    dt_obj = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_obj = tz.localize(dt_obj)

    solar = Solar.fromYmdHms(
        dt_obj.year, dt_obj.month, dt_obj.day,
        dt_obj.hour, dt_obj.minute, 0
    )

    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()

    day_stem = eight_char.getDayGan()
    day_element, _ = STEM_INFO[day_stem]

    return {
        "eight_char": eight_char,
        "day_stem": day_stem,
        "day_element": day_element
    }

def classify_elements(day_element, strength_type, climate_element):

    favorable = []
    harmful = []
    neutral = []

    if strength_type == "Strong (신강)":
        favorable = [CONTROLS[day_element], GENERATES[day_element]]
        harmful = [day_element]

        for k, v in GENERATES.items():
            if v == day_element:
                harmful.append(k)

    else:
        resource = None
        for k, v in GENERATES.items():
            if v == day_element:
                resource = k
        favorable = [day_element, resource]
        harmful = [CONTROLS[day_element], GENERATES[day_element]]

    if climate_element and climate_element not in favorable:
        favorable.append(climate_element)

    for e in ALL_ELEMENTS:
        if e not in favorable and e not in harmful:
            neutral.append(e)

    return {
        "희신": favorable,
        "기신": harmful,
        "중립": neutral
    }


@app.get("/calculate-saju")
def calculate_saju(birth_date: str, birth_time: str, timezone: str, gender: int):

    tz = pytz.timezone(timezone)
    dt_obj = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_obj = tz.localize(dt_obj)

    solar = Solar.fromYmdHms(
        dt_obj.year, dt_obj.month, dt_obj.day,
        dt_obj.hour, dt_obj.minute, 0
    )

    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()

    year_stem = eight_char.getYearGan()
    month_stem = eight_char.getMonthGan()
    day_stem = eight_char.getDayGan()
    hour_stem = eight_char.getTimeGan()

    visible_stems = [year_stem, month_stem, day_stem, hour_stem]

    # Basic strength
    score = 0
    day_element, _ = STEM_INFO[day_stem]

    for stem in visible_stems:
        element, _ = STEM_INFO[stem]
        if element == day_element:
            score += 2
        elif GENERATES[element] == day_element:
            score += 1
        elif CONTROLS[element] == day_element:
            score -= 2

    strength_type = "Strong (신강)" if score > 0 else "Weak (신약)"

    # Climate (simple)
    month_branch = eight_char.getMonthZhi()
    climate_element = None
    if month_branch in ["巳", "午"]:
        climate_element = "Water"
    elif month_branch in ["亥", "子"]:
        climate_element = "Fire"

    element_roles = classify_elements(day_element, strength_type, climate_element)

    # 대운
    yun = eight_char.getYun(gender)
    da_yun_list = []
    for da in yun.getDaYun():
        da_yun_list.append({
            "pillar": da.getGanZhi(),
            "start_age": da.getStartAge()
        })

    # Current Year 세운
    current_year = dt.date.today().year
    current_solar = Solar.fromYmd(current_year, 1, 1)
    current_lunar = current_solar.getLunar()
    current_year_ganzhi = current_lunar.getYearInGanZhi()

    current_year_stem = current_year_ganzhi[0]
    current_element, _ = STEM_INFO[current_year_stem]

    current_influence = "Supportive year" if current_element == day_element else "Challenging year"

    return {
        "four_pillars": {
            "year": eight_char.getYear(),
            "month": eight_char.getMonth(),
            "day": eight_char.getDay(),
            "hour": eight_char.getTime()
        },
        "day_master": {
            "stem": day_stem,
            "element": day_element
        },
        "strength": {
            "score": score,
            "type": strength_type
        },
        "element_roles": element_roles,
        "da_yun_cycles": da_yun_list,
        "current_year": {
            "year": current_year,
            "ganzhi": current_year_ganzhi,
            "influence": current_influence
        }
    }

# =====================================
# COMPATIBILITY ENDPOINT
# =====================================

@app.get("/compatibility")
def compatibility(
    birth_date1: str,
    birth_time1: str,
    timezone1: str,
    gender1: int,
    birth_date2: str,
    birth_time2: str,
    timezone2: str,
    gender2: int
):

    person1 = build_chart(birth_date1, birth_time1, timezone1, gender1)
    person2 = build_chart(birth_date2, birth_time2, timezone2, gender2)

    score = 50  # neutral base

    # Element harmony
    if GENERATES[person1["day_element"]] == person2["day_element"]:
        score += 15
    elif CONTROLS[person1["day_element"]] == person2["day_element"]:
        score -= 15

    if GENERATES[person2["day_element"]] == person1["day_element"]:
        score += 15
    elif CONTROLS[person2["day_element"]] == person1["day_element"]:
        score -= 15

    # Clamp score
    score = max(0, min(100, score))

    if score >= 75:
        tier = "High Compatibility"
    elif score >= 50:
        tier = "Moderate Compatibility"
    else:
        tier = "Challenging Dynamic"

    dynamic = "Balanced and mutually supportive" if score >= 75 else \
              "Growth-oriented but requires effort" if score >= 50 else \
              "Strong attraction but potential tension"

    return {
        "compatibility_score": score,
        "compatibility_tier": tier,
        "relationship_dynamic": dynamic,
        "element_interaction": {
            "person1_element": person1["day_element"],
            "person2_element": person2["day_element"]
        }
    }

# =====================================
# RELATIONSHIP TIMING ENDPOINT
# =====================================

@app.get("/relationship-timing")
def relationship_timing(
    birth_date: str,
    birth_time: str,
    timezone: str,
    gender: int
):

    chart = build_chart(birth_date, birth_time, timezone, gender)

    day_element = chart["day_element"]

    # Determine spouse element
    if gender == 0:  # Female → Officer (controls Day Master)
        spouse_element = CONTROLS[day_element]
        spouse_type = "Officer Star (관성)"
    else:  # Male → Wealth (controlled by Day Master)
        spouse_element = GENERATES[CONTROLS[day_element]]
        spouse_type = "Wealth Star (재성)"

    # Current year
    current_year = dt.date.today().year
    current_solar = Solar.fromYmd(current_year, 1, 1)
    current_lunar = current_solar.getLunar()
    current_year_ganzhi = current_lunar.getYearInGanZhi()

    year_stem = current_year_ganzhi[0]
    year_element, _ = STEM_INFO[year_stem]

    activation_score = 50

    if year_element == spouse_element:
        activation_score += 25
    elif GENERATES[year_element] == spouse_element:
        activation_score += 15
    elif CONTROLS[year_element] == spouse_element:
        activation_score -= 15

    activation_score = max(0, min(100, activation_score))

    if activation_score >= 75:
        tier = "Strong Romantic Activation"
        marriage_window = "High probability within 1–2 years"
    elif activation_score >= 50:
        tier = "Moderate Romantic Energy"
        marriage_window = "Possible relationship growth phase"
    else:
        tier = "Low Romantic Activation"
        marriage_window = "Focus on personal development first"

    return {
        "spouse_star_type": spouse_type,
        "spouse_element": spouse_element,
        "current_year_element": year_element,
        "romantic_activation_score": activation_score,
        "activation_tier": tier,
        "marriage_window_assessment": marriage_window
    }