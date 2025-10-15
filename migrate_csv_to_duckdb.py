"""
Migrate CSV data to DuckDB
"""
import duckdb
import polars as pl
from pathlib import Path

CSV_FILE = "tibber_consumption_data.csv"
DB_FILE = "tibber_data.duckdb"


def migrate():
    """Migrate CSV data to DuckDB"""
    csv_path = Path(CSV_FILE)
    db_path = Path(DB_FILE)

    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return

    if db_path.exists():
        response = input(f"⚠️  Database {db_path} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Migration cancelled")
            return
        db_path.unlink()

    print(f"📖 Reading CSV file: {csv_path}")
    df = pl.read_csv(csv_path, separator='\t')
    print(f"   Found {len(df)} records")

    # Rename columns to match DuckDB schema
    df_renamed = df.rename({
        'from': 'from_time',
        'to': 'to_time',
        'consumptionUnit': 'consumption_unit',
        'unitPrice': 'unit_price',
        'unitPriceVAT': 'unit_price_vat'
    })

    print(f"💾 Creating database: {db_path}")
    con = duckdb.connect(str(db_path))

    # Create tables
    print("📊 Creating tables...")
    con.execute("""
        CREATE TABLE IF NOT EXISTS hourly_consumption (
            from_time TIMESTAMP WITH TIME ZONE,
            to_time TIMESTAMP WITH TIME ZONE,
            consumption DOUBLE,
            consumption_unit VARCHAR,
            cost DOUBLE,
            unit_price DOUBLE,
            unit_price_vat DOUBLE,
            currency VARCHAR,
            PRIMARY KEY (from_time, to_time)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_consumption (
            date DATE,
            total_consumption DOUBLE,
            total_cost DOUBLE,
            avg_unit_price DOUBLE,
            currency VARCHAR,
            PRIMARY KEY (date)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS monthly_consumption (
            year INTEGER,
            month INTEGER,
            total_consumption DOUBLE,
            total_cost DOUBLE,
            avg_unit_price DOUBLE,
            currency VARCHAR,
            PRIMARY KEY (year, month)
        )
    """)

    # Insert data
    print("📥 Inserting data...")
    con.execute("""
        INSERT INTO hourly_consumption
        SELECT * FROM df_renamed
    """)

    # Create aggregations
    print("📊 Creating daily aggregations...")
    con.execute("""
        INSERT INTO daily_consumption
        SELECT
            CAST(from_time AS DATE) as date,
            SUM(consumption) as total_consumption,
            SUM(cost) as total_cost,
            AVG(unit_price) as avg_unit_price,
            MAX(currency) as currency
        FROM hourly_consumption
        WHERE consumption IS NOT NULL
        GROUP BY CAST(from_time AS DATE)
    """)

    print("📊 Creating monthly aggregations...")
    con.execute("""
        INSERT INTO monthly_consumption
        SELECT
            EXTRACT(YEAR FROM from_time) as year,
            EXTRACT(MONTH FROM from_time) as month,
            SUM(consumption) as total_consumption,
            SUM(cost) as total_cost,
            AVG(unit_price) as avg_unit_price,
            MAX(currency) as currency
        FROM hourly_consumption
        WHERE consumption IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM from_time), EXTRACT(MONTH FROM from_time)
    """)

    # Print stats
    hourly_count = con.execute("SELECT COUNT(*) FROM hourly_consumption").fetchone()[0]
    daily_count = con.execute("SELECT COUNT(*) FROM daily_consumption").fetchone()[0]
    monthly_count = con.execute("SELECT COUNT(*) FROM monthly_consumption").fetchone()[0]

    print("\n✅ Migration complete!")
    print(f"   Hourly records: {hourly_count}")
    print(f"   Daily records: {daily_count}")
    print(f"   Monthly records: {monthly_count}")

    # Show date range
    result = con.execute("""
        SELECT
            MIN(from_time) as start_date,
            MAX(from_time) as end_date,
            SUM(consumption) as total_kwh,
            SUM(cost) as total_cost
        FROM hourly_consumption
    """).fetchone()

    print(f"\n📅 Date range: {result[0]} to {result[1]}")
    print(f"⚡ Total consumption: {result[2]:.2f} kWh")
    print(f"💰 Total cost: {result[3]:.2f}")

    con.close()


if __name__ == "__main__":
    migrate()
