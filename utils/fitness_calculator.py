import math
from typing import Dict


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Body Mass Index."""
    if height_cm <= 0:
        raise ValueError("height_cm must be positive")
    height_m = height_cm / 100.0
    return weight_kg / (height_m**2)


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor BMR equation."""
    gender = gender.lower()
    if gender == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        # female and other – use female constant as conservative default
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calculate_tdee(bmr: float, activity_level: float) -> float:
    """Total Daily Energy Expenditure from BMR and activity multiplier."""
    if activity_level <= 0:
        raise ValueError("activity_level must be positive")
    return bmr * activity_level


def calculate_macros(tdee: float, goal: str) -> Dict[str, float]:
    """
    Simple macro split based on goal.

    Returns grams per day:
    - protein_g
    - carbs_g
    - fats_g
    - calories
    """
    goal_lower = goal.lower()

    # Default macro splits
    if "loss" in goal_lower or "cut" in goal_lower or "fat" in goal_lower:
        # Higher protein, moderate fat, lower carbs
        protein_pct = 0.32
        fat_pct = 0.25
    elif "gain" in goal_lower or "bulk" in goal_lower:
        protein_pct = 0.27
        fat_pct = 0.23
    else:
        # Recomp / maintenance
        protein_pct = 0.30
        fat_pct = 0.25

    carbs_pct = 1.0 - protein_pct - fat_pct

    protein_cal = tdee * protein_pct
    fat_cal = tdee * fat_pct
    carbs_cal = tdee * carbs_pct

    protein_g = protein_cal / 4.0
    carbs_g = carbs_cal / 4.0
    fats_g = fat_cal / 9.0

    return {
        "protein_g": round(protein_g),
        "carbs_g": round(carbs_g),
        "fats_g": round(fats_g),
        "calories": round(tdee),
    }


def estimate_body_fat(measurements: Dict[str, float], gender: str, age: int) -> float | None:
    """
    Estimate body fat % using US Navy method if required measurements are provided.

    Expects:
    - measurements['waist_cm']
    - measurements['neck_cm']
    - measurements['height_cm']
    - For females also measurements['hip_cm'] (or 'hips_cm')
    """
    gender = gender.lower()
    try:
        waist = float(measurements.get("waist_cm"))
        neck = float(measurements.get("neck_cm"))
        height = float(measurements.get("height_cm"))
    except (TypeError, ValueError):
        return None

    if gender == "male":
        # US Navy male
        if waist <= 0 or neck <= 0 or height <= 0:
            return None
        bf = 495 / (
            1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)
        ) - 450
        return round(bf, 1)
    else:
        # US Navy female
        hip = measurements.get("hip_cm") or measurements.get("hips_cm")
        try:
            hip = float(hip)
        except (TypeError, ValueError):
            return None
        if waist <= 0 or neck <= 0 or height <= 0 or hip <= 0:
            return None
        bf = 495 / (
            1.29579
            - 0.35004 * math.log10(waist + hip - neck)
            + 0.22100 * math.log10(height)
        ) - 450
        return round(bf, 1)


def calculate_one_rep_max(weight: float, reps: int) -> float:
    """Epley formula for 1RM."""
    if reps <= 0:
        raise ValueError("reps must be positive")
    return round(weight * (1 + reps / 30.0), 1)


def weeks_to_goal(
    current_weight: float, target_weight: float, goal_type: str
) -> float:
    """
    Rough estimate of weeks to goal based on safe rate of change.

    - For fat loss: assume ~0.75% of bodyweight per week.
    - For gain: assume ~0.25–0.5% per week (use 0.4%).
    """
    if current_weight <= 0:
        raise ValueError("current_weight must be positive")

    diff = target_weight - current_weight
    if diff == 0:
        return 0.0

    goal_type_lower = goal_type.lower()
    if "loss" in goal_type_lower or "cut" in goal_type_lower or diff < 0:
        weekly_change = abs(current_weight * 0.0075)
    else:
        weekly_change = abs(current_weight * 0.004)

    if weekly_change == 0:
        return 0.0

    weeks = abs(diff) / weekly_change
    return round(weeks, 1)



