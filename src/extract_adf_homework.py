import pyodbc
print("Connecting to SQL Server...") # Connect to the SQL Server database
conn =pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-2Q4USBO;"
    "DATABASE=GradeFlow-Operations;"
    "Trusted_Connection=yes;"
)
print("Connected to SQL Server!") # Create a cursor object to execute SQL queries
