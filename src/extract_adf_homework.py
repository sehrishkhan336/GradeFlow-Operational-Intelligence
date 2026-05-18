import os
import sys
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_analytics_url() -> str:
    analytics_server = require_env("DB_ANALYTICS_SERVER")
    analytics_database = require_env("DB_ANALYTICS_DATABASE")
    analytics_username = os.getenv("DB_ANALYTICS_USERNAME")
    analytics_password = os.getenv("DB_ANALYTICS_PASSWORD")
    analytics_trusted = os.getenv("DB_ANALYTICS_TRUSTED_CONNECTION", "yes").lower() in {"1", "true", "yes"}

    if analytics_trusted:
        return URL.create(
            "mssql+pyodbc",
            username=None,
            password=None,
            host=analytics_server,
            database=analytics_database,
            query={"driver": "ODBC Driver 17 for SQL Server", "trusted_connection": "yes"},
        )

    if analytics_username is None or analytics_password is None:
        raise RuntimeError(
            "Analytics DB authentication requires DB_ANALYTICS_USERNAME and DB_ANALYTICS_PASSWORD when not using trusted connection"
        )

    return URL.create(
        "mssql+pyodbc",
        username=analytics_username,
        password=analytics_password,
        host=analytics_server,
        database=analytics_database,
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )


if __name__ == "__main__":
    try:
        server = require_env("DB_SERVER")
        database = require_env("DB_DATABASE")
        username = require_env("DB_USERNAME")
        password = require_env("DB_PASSWORD")

        print("Connecting to SQL Server...")
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
        )
        print("Connection successful!")

        print("Creating analytics database engine...")
        analytics_engine = create_engine(build_analytics_url())

        print("Testing analytics database connection...")
        with analytics_engine.connect() as analytics_conn:
            analytics_conn.exec_driver_sql("SELECT 1")
        print("Analytics database connection successful!")

    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
