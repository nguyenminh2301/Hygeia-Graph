"""Example datasets registry and loader for Hygeia-Graph."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Get assets directory
ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"


# Example metadata registry
EXAMPLES: List[Dict[str, Any]] = [
    {
        "key": "easy",
        "title": "Easy — Inflammation & Sleep (Mini demo)",
        "filename": "example_easy.csv",
        "rows_expected": (120, 160),
        "goal": "Demonstrate mixed MGM types and a simple interpretable network.",
        "notes": [
            "No missing values.",
            "Good for first-time users.",
            "6 variables: Age, CRP, Gender, SleepQuality, HospitalDays, PainScore",
        ],
        "recommended_settings": {"threshold": 0.0, "top_edges": 200},
    },
    {
        "key": "medium",
        "title": "Medium — Metabolic–Mood Comorbidity",
        "filename": "example_medium.csv",
        "rows_expected": (220, 320),
        "goal": "Show multi-domain interactions and potential bridge nodes.",
        "notes": [
            "Balanced categories to avoid rare-class warnings.",
            "12 variables across Demographics, Biomarkers, Symptoms, Lifestyle domains.",
        ],
        "recommended_settings": {"threshold": 0.05, "top_edges": 500},
    },
    {
        "key": "hard",
        "title": "Hard — Multi-domain Hairball Stress Test",
        "filename": "example_hard.csv",
        "rows_expected": (500, 800),
        "goal": "Stress test thresholding/top-edge limits and LASSO funnel.",
        "notes": [
            "Use threshold slider to reduce hairball.",
            "Consider LASSO feature selection if p is high.",
            "30 variables across 5 domain groups.",
        ],
        "recommended_settings": {"threshold": 0.1, "top_edges": 1000},
    },
]


def get_example_keys() -> List[str]:
    """Get list of example keys."""
    return [ex["key"] for ex in EXAMPLES]


def get_example_meta(key: str) -> Optional[Dict[str, Any]]:
    """Get metadata for an example by key.

    Args:
        key: Example key (easy, medium, hard).

    Returns:
        Metadata dict or None if not found.
    """
    for ex in EXAMPLES:
        if ex["key"] == key:
            return ex
    return None


def get_example_path(key: str) -> Optional[Path]:
    """Get file path for an example.

    Args:
        key: Example key.

    Returns:
        Path object or None if not found.
    """
    meta = get_example_meta(key)
    if meta:
        return ASSETS_DIR / meta["filename"]
    return None


def load_example_df(key: str) -> pd.DataFrame:
    """Load example dataset as DataFrame.

    Args:
        key: Example key (easy, medium, hard).

    Returns:
        Loaded DataFrame.

    Raises:
        ValueError: If key not found.
        FileNotFoundError: If file doesn't exist.
    """
    path = get_example_path(key)
    if path is None:
        raise ValueError(f"Unknown example key: {key}")

    if not path.exists():
        raise FileNotFoundError(f"Example file not found: {path}")

    return pd.read_csv(path)


def validate_generated_data(df: pd.DataFrame, min_categories: int = 2) -> bool:
    """Validate generated data has minimum variation."""
    for col in df.columns:
        unique_count = df[col].nunique()
        if unique_count < min_categories:
            raise ValueError(f"Column '{col}' has only {unique_count} unique value(s). Minimum required: {min_categories}")
    return True


def generate_easy_dataset(seed: int = 2024) -> pd.DataFrame:
    """Generate the Easy example dataset."""
    np.random.seed(seed)
    n = 140

    # Base variables
    age = np.random.normal(50, 15, n).clip(18, 85).round(1)
    gender = np.random.choice(["Male", "Female"], n, p=[0.48, 0.52])

    # CRP correlates with age
    crp = (0.5 + 0.02 * age + np.random.exponential(2, n)).clip(0.1, 25).round(2)

    # Pain correlates with CRP
    pain = (crp * 0.3 + np.random.normal(0, 1.5, n)).clip(0, 10).round(1)

    # Hospital days correlate with pain and CRP
    hospital_days = (pain * 0.5 + crp * 0.2 + np.random.poisson(2, n)).clip(0, 30).astype(int)

    # Sleep quality inversely correlates with pain
    sleep_raw = 5 - pain * 0.3 + np.random.normal(0, 0.8, n)
    sleep_quality = sleep_raw.clip(1, 5).round().astype(int)

    df = pd.DataFrame({
        "Age": age,
        "Gender": gender,
        "CRP": crp,
        "PainScore": pain,
        "HospitalDays": hospital_days,
        "SleepQuality": sleep_quality,
    })

    validate_generated_data(df)
    return df


def generate_medium_dataset(seed: int = 2025) -> pd.DataFrame:
    """Generate the Medium example dataset."""
    np.random.seed(seed)
    n = 280

    # Demographics
    age = np.random.normal(52, 14, n).clip(20, 80).round(1)
    gender = np.random.choice(["Male", "Female"], n, p=[0.45, 0.55])

    # Biomarkers
    bmi = np.random.normal(27, 5, n).clip(18, 45).round(1)
    hba1c = (5.0 + bmi * 0.05 + np.random.normal(0, 0.8, n)).clip(4, 12).round(1)
    crp = (0.3 + bmi * 0.1 + np.random.exponential(1.5, n)).clip(0.1, 20).round(2)

    # Symptoms (correlated cluster)
    anxiety_base = crp * 0.3 + np.random.normal(5, 2, n)
    anxiety = anxiety_base.clip(0, 10).round(1)
    depression = (anxiety * 0.6 + np.random.normal(0, 1.5, n)).clip(0, 10).round(1)
    insomnia = (anxiety * 0.4 + depression * 0.3 + np.random.normal(0, 1.5, n)).clip(0, 10).round(1)

    # Lifestyle
    smoking = np.random.choice(["Never", "Former", "Current"], n, p=[0.5, 0.3, 0.2])
    exercise = np.random.choice([1, 2, 3, 4], n, p=[0.2, 0.35, 0.3, 0.15])

    # Utilisation
    hospital_days = (depression * 0.3 + crp * 0.2 + np.random.poisson(1, n)).clip(0, 20).astype(int)

    # Diagnosis stage
    diagnosis_stage = np.random.choice([1, 2, 3, 4], n, p=[0.3, 0.35, 0.25, 0.1])

    df = pd.DataFrame({
        "Age": age,
        "Gender": gender,
        "BMI": bmi,
        "HbA1c": hba1c,
        "CRP": crp,
        "AnxietyScore": anxiety,
        "DepressionScore": depression,
        "InsomniaScore": insomnia,
        "SmokingStatus": smoking,
        "ExerciseLevel": exercise,
        "HospitalDays": hospital_days,
        "DiagnosisStage": diagnosis_stage,
    })

    validate_generated_data(df)
    return df


def generate_hard_dataset(seed: int = 2028) -> pd.DataFrame:
    """Generate the Hard example dataset."""
    np.random.seed(seed)
    n = 600

    data = {}

    # Demographics (3)
    data["Age"] = np.random.normal(55, 12, n).clip(25, 80).round(1)
    data["Gender"] = np.random.choice(["Male", "Female"], n, p=[0.48, 0.52])
    data["Ethnicity"] = np.random.choice(["White", "Black", "Asian", "Hispanic", "Other"], n, p=[0.4, 0.2, 0.15, 0.15, 0.1])

    # Biomarkers (10)
    data["BMI"] = np.random.normal(28, 6, n).clip(17, 50).round(1)
    data["SystolicBP"] = (120 + data["Age"] * 0.3 + data["BMI"] * 0.5 + np.random.normal(0, 12, n)).clip(90, 200).round()
    data["DiastolicBP"] = (data["SystolicBP"] * 0.6 + np.random.normal(0, 8, n)).clip(50, 120).round()
    data["HeartRate"] = np.random.normal(72, 12, n).clip(45, 120).round()
    data["HbA1c"] = (5.2 + data["BMI"] * 0.04 + np.random.normal(0, 0.7, n)).clip(4, 13).round(1)
    data["Cholesterol"] = np.random.normal(200, 40, n).clip(120, 350).round()
    data["LDL"] = (data["Cholesterol"] * 0.6 + np.random.normal(0, 15, n)).clip(50, 200).round()
    data["HDL"] = np.random.normal(55, 15, n).clip(25, 100).round()
    data["CRP"] = np.random.exponential(2, n).clip(0.1, 25).round(2)
    data["Glucose"] = (90 + data["HbA1c"] * 10 + np.random.normal(0, 15, n)).clip(60, 250).round()

    # Symptoms (12)
    data["PainScore"] = (data["CRP"] * 0.3 + np.random.normal(3, 2, n)).clip(0, 10).round(1)
    data["FatigueScore"] = (data["PainScore"] * 0.4 + np.random.normal(4, 2, n)).clip(0, 10).round(1)
    data["AnxietyScore"] = np.random.normal(4, 2.5, n).clip(0, 10).round(1)
    data["DepressionScore"] = (data["AnxietyScore"] * 0.5 + np.random.normal(0, 1.5, n)).clip(0, 10).round(1)
    data["InsomniaScore"] = (data["AnxietyScore"] * 0.3 + data["PainScore"] * 0.2 + np.random.normal(3, 2, n)).clip(0, 10).round(1)
    data["AppetiteLoss"] = np.random.choice([0, 1, 2, 3], n, p=[0.4, 0.3, 0.2, 0.1])
    data["Nausea"] = np.random.choice([0, 1, 2, 3], n, p=[0.5, 0.25, 0.15, 0.1])
    data["Headache"] = np.random.choice([0, 1, 2, 3, 4], n, p=[0.3, 0.25, 0.2, 0.15, 0.1])
    data["Dizziness"] = np.random.choice([0, 1, 2, 3], n, p=[0.45, 0.3, 0.15, 0.1])
    data["BreathShortness"] = np.random.choice([0, 1, 2, 3], n, p=[0.5, 0.25, 0.15, 0.1])
    data["JointPain"] = (data["Age"] * 0.05 + np.random.normal(3, 2, n)).clip(0, 10).round(1)
    data["MusclePain"] = (data["FatigueScore"] * 0.3 + np.random.normal(3, 2, n)).clip(0, 10).round(1)

    # Lifestyle (4)
    data["SmokingStatus"] = np.random.choice(["Never", "Former", "Current"], n, p=[0.45, 0.35, 0.2])
    data["AlcoholUse"] = np.random.choice(["Non-drinker", "Light", "Moderate", "Heavy"], n, p=[0.25, 0.4, 0.25, 0.1])
    data["ExerciseLevel"] = np.random.choice([1, 2, 3, 4], n, p=[0.25, 0.35, 0.25, 0.15])
    data["DietQuality"] = np.random.choice([1, 2, 3, 4, 5], n, p=[0.1, 0.2, 0.35, 0.25, 0.1])

    # Utilisation (3)
    data["HospitalDays"] = (data["PainScore"] * 0.3 + np.random.poisson(2, n)).clip(0, 30).astype(int)
    data["ERVisits"] = np.random.poisson(1, n).clip(0, 10).astype(int)
    data["MedicationCount"] = (data["Age"] * 0.05 + np.random.poisson(2, n)).clip(0, 8).astype(int)

    df = pd.DataFrame(data)
    validate_generated_data(df)
    return df
