import os
import sys
import pandas as pd 
import pyodbc
from dotenv import load_dotenv

# =========================================================
# Load environment variables from src/.env
# =========================================================
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

# =========================================================
# Validate required environment variables   
# Prevents silent failures due to missing configuration
# =========================================================

def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value

# =========================================================


# =========================================================
def read_homework_ids(csv_path: str) -> list[int]:
    df = pd.read_csv(csv_path)

    if "HomeworkID" not in df.columns:
        raise RuntimeError("HomeworkID column not found in raw CSV.")

    homework_ids = (
        df["HomeworkID"]
        .dropna()
        .astype(int)
        .drop_duplicates()
        .tolist()
    )

    print(f"Loaded {len(homework_ids):,} unique HomeworkIDs from raw CSV.")

    return homework_ids

# =========================================================


# =========================================================

def main() -> int:
    raw_csv_path = os.path.join(
        "data",
        "gradeflow_raw_homework_before_after.csv"
    )

    homework_ids = read_homework_ids(raw_csv_path)

    print("First 5 HomeworkIDs:", homework_ids[:5])

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
       
        