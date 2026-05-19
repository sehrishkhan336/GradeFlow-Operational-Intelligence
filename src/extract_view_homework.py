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
# Connect to source SQL Server using pyodbc
# =========================================================
def connect_to_source_db():
    server = require_env("DB_SERVER")
    database = require_env("DB_DATABASE")
    username = require_env("DB_USERNAME")
    password = require_env("DB_PASSWORD")

    print("Connecting to source SQL Server...")

    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
    )

    print("Source SQL Server connection successful!")

    return conn
# =========================================================
# Read ClassSignupsIDs from raw CSV file
# =========================================================
def read_classsignup_ids(csv_path: str) -> list[int]:
    df = pd.read_csv(csv_path)

    if "ClassSignupsID" not in df.columns:
        raise RuntimeError("ClassSignupsID column not found in raw CSV.")

    classsignup_ids = (
        df["ClassSignupsID"]
        .dropna()
        .astype(int)
        .drop_duplicates()
        .tolist()
    )

    print(f"Loaded {len(classsignup_ids):,} unique ClassSignupsIDs from raw CSV.")

    return classsignup_ids

# =========================================================
# Extract ClassSignupsID enrichment from ADF_Homework self-lookup
# =========================================================
def extract_classsignup_enrichment_data(conn, classsignup_ids: list[int]) -> pd.DataFrame:
    if not classsignup_ids:
        raise RuntimeError("No ClassSignupsIDs found to enrich.")

    id_list = ",".join(str(sid) for sid in classsignup_ids)

    query = f"""
        WITH StudentLookup AS (
            SELECT
                ClassSignupsID,
                MAX(StudentUserID) AS StudentUserID,
                MAX(StudentName)   AS StudentName,
                MAX(StudentEmail)  AS StudentEmail,
                MAX(SectionName)   AS SectionName
            FROM dbo.ADF_Homework
            WHERE ClassSignupsID IS NOT NULL
              AND (
                    StudentUserID IS NOT NULL
                 OR StudentName   IS NOT NULL
                 OR StudentEmail  IS NOT NULL
                 OR SectionName   IS NOT NULL
              )
            GROUP BY ClassSignupsID
        )
        SELECT
            ClassSignupsID,
            StudentUserID,
            StudentName,
            StudentEmail,
            SectionName
        FROM StudentLookup
        WHERE ClassSignupsID IN ({id_list});
    """

    print("Extracting ClassSignupsID enrichment data...")

    df = pd.read_sql_query(query, conn)

    print(f"Extracted {len(df):,} enrichment records from ADF_Homework lookup.")

    if len(df) == 0:
        print("WARNING: No enrichment records found. Check ClassSignupsID lookup in ADF_Homework.")

    return df
# =========================================================
# Export DataFrame to CSV
# =========================================================
def export_dataframe_to_csv(df: pd.DataFrame, output_path: str) -> None:
    output_dir = os.path.dirname(output_path) or "data"
    os.makedirs(output_dir, exist_ok=True)

    df.to_csv(output_path, index=False)

    print(f"Exported {len(df):,} rows to {output_path}")

# =========================================================
# Main execution flow
# =========================================================
def main() -> int:
    conn = None

    try:
        raw_csv_path = os.path.join(
            "data",
            "gradeflow_raw_homework_before_after.csv"
        )

        output_path = os.path.join(
            "data",
            "gradeflow_view_homework_enrichment.csv"
        )

        classsignup_ids = read_classsignup_ids(raw_csv_path)
        conn = connect_to_source_db()

        enrichment_df = extract_view_homework_data(conn, classsignup_ids)

        export_dataframe_to_csv(enrichment_df, output_path)

        print("vw_Homework enrichment extraction completed successfully.")

        return 0

    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    finally:
        if conn is not None:
            conn.close()
            print("Closed source SQL Server connection.")
#========================================================
# Entry point
#========================================================
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)