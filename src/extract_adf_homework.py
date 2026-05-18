# =========================================================
# GradeFlow Operational Intelligence
# Raw Operational Data Extraction Pipeline
#
# Purpose:
# Extract ADF_Homework operational grading data,
# filter reporting periods,
# validate analytics connectivity,
# and export raw data to CSV for downstream BI modeling.
# =========================================================

import os
import sys
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
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
# Build SQLAlchemy connection URL for analytics database
#
# Supports:
# - Windows Trusted Authentication
# - SQL Authentication
# =========================================================
def build_analytics_url() -> URL:

    analytics_server = require_env("DB_ANALYTICS_SERVER")
    analytics_database = require_env("DB_ANALYTICS_DATABASE")

    analytics_username = os.getenv("DB_ANALYTICS_USERNAME")
    analytics_password = os.getenv("DB_ANALYTICS_PASSWORD")

    analytics_trusted = (
        os.getenv(
            "DB_ANALYTICS_TRUSTED_CONNECTION",
            "yes"
        ).lower() in {"1", "true", "yes"}
    )

    # -----------------------------------------------------
    # Windows Trusted Authentication
    # -----------------------------------------------------
    if analytics_trusted:

        return URL.create(
            "mssql+pyodbc",
            host=analytics_server,
            database=analytics_database,
            query={
                "driver": "ODBC Driver 17 for SQL Server",
                "trusted_connection": "yes",
            },
        )

    # -----------------------------------------------------
    # SQL Authentication Validation
    # -----------------------------------------------------
    if analytics_username is None or analytics_password is None:

        raise RuntimeError(
            "Analytics DB authentication requires "
            "DB_ANALYTICS_USERNAME and "
            "DB_ANALYTICS_PASSWORD"
        )

    # -----------------------------------------------------
    # SQL Authentication Connection
    # -----------------------------------------------------
    return URL.create(
        "mssql+pyodbc",
        username=analytics_username,
        password=analytics_password,
        host=analytics_server,
        database=analytics_database,
        query={
            "driver": "ODBC Driver 17 for SQL Server"
        },
    )


# =========================================================
# Extract operational homework grading data
#
# Reporting Windows:
# - Before AI Grader
# - After AI Grader
#
# January intentionally excluded due to
# production transition period.
# =========================================================
def extract_homework_data(conn) -> pd.DataFrame:

    query = """

        SELECT *,

            CASE

                WHEN DateEntered BETWEEN
                    '2025-10-01'
                    AND '2025-12-21'

                THEN 'Before AI Grader'

                WHEN DateEntered BETWEEN
                    '2026-02-01'
                    AND '2026-04-30'

                THEN 'After AI Grader'

                ELSE 'Excluded'

            END AS ReportingPeriod

        FROM ADF_Homework

        WHERE (

            DateEntered BETWEEN
                '2025-10-01'
                AND '2025-12-21'

            OR

            DateEntered BETWEEN
                '2026-02-01'
                AND '2026-04-30'

        )

        AND MONTH(DateEntered) <> 1

    """

    return pd.read_sql_query(query, conn)


# =========================================================
# Export dataframe to CSV
#
# Creates output folder automatically if missing.
# =========================================================
def export_dataframe_to_csv(
    df: pd.DataFrame,
    output_path: str
) -> None:

    try:

        output_dir = (
            os.path.dirname(output_path)
            or "data"
        )

        os.makedirs(output_dir, exist_ok=True)

        df.to_csv(output_path, index=False)

        print(
            f"Exported {len(df):,} rows "
            f"to {output_path}"
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to export DataFrame to CSV: {exc}"
        ) from exc


# =========================================================
# Main execution workflow
#
# Steps:
# 1. Connect to source operational database
# 2. Validate analytics database connection
# 3. Extract filtered operational data
# 4. Export raw dataset to CSV
# 5. Cleanup resources
# =========================================================
def main() -> int:

    conn = None
    analytics_engine = None

    output_path = os.path.join(
        "data",
        "gradeflow_raw_homework_before_after.csv"
    )

    try:

        # -------------------------------------------------
        # Load source database credentials
        # -------------------------------------------------
        server = require_env("DB_SERVER")
        database = require_env("DB_DATABASE")
        username = require_env("DB_USERNAME")
        password = require_env("DB_PASSWORD")

        # -------------------------------------------------
        # Connect to operational SQL Server
        # -------------------------------------------------
        print("Connecting to source SQL Server...")

        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
        )

        print(
            "Source SQL Server connection successful!"
        )

        # -------------------------------------------------
        # Create analytics database engine
        # -------------------------------------------------
        print(
            "Creating analytics database engine..."
        )

        analytics_engine = create_engine(
            build_analytics_url()
        )

        # -------------------------------------------------
        # Validate analytics database connectivity
        # -------------------------------------------------
        print(
            "Testing analytics database connection..."
        )

        with analytics_engine.connect() as analytics_conn:

            analytics_conn.exec_driver_sql(
                "SELECT 1"
            )

        print(
            "Analytics database connection successful!"
        )

        # -------------------------------------------------
        # Extract operational grading data
        # -------------------------------------------------
        print("Extracting ADF_Homework data...")

        df = extract_homework_data(conn)

        print(
            f"Extracted {len(df):,} records "
            f"from ADF_Homework."
        )

        # -------------------------------------------------
        # Export raw operational dataset
        # -------------------------------------------------
        print("Exporting data to CSV...")

        export_dataframe_to_csv(df, output_path)

        print(
            "Data extraction and export completed "
            "successfully."
        )

        return 0

    except Exception as exc:

        print(f"Error: {exc}")

        return 1

    finally:

        # -------------------------------------------------
        # Cleanup source SQL connection
        # -------------------------------------------------
        if conn is not None:

            conn.close()

            print(
                "Closed source SQL Server connection."
            )

        # -------------------------------------------------
        # Cleanup analytics SQLAlchemy engine
        # -------------------------------------------------
        if analytics_engine is not None:

            analytics_engine.dispose()

            print("Disposed analytics engine.")


# =========================================================
# Application Entry Point
# =========================================================
if __name__ == "__main__":

    sys.exit(main())