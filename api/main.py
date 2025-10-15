"""
FastAPI application for Tibber energy consumption data
"""
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
import duckdb
import os
from pathlib import Path

# Configuration
DB_PATH = os.getenv('DATABASE_PATH', '../tibber_data.duckdb')
API_KEY = os.getenv('API_KEY', None)  # Set API_KEY environment variable to enable authentication

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(
    title="Tibber Energy API",
    description="API for querying Tibber energy consumption data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for responses
class HourlyConsumption(BaseModel):
    from_time: datetime
    to_time: datetime
    consumption: Optional[float]
    consumption_unit: str
    cost: Optional[float]
    unit_price: float
    unit_price_vat: float
    currency: str


class DailyConsumption(BaseModel):
    date: date
    total_consumption: float
    total_cost: float
    avg_unit_price: float
    currency: str


class MonthlyConsumption(BaseModel):
    year: int
    month: int
    total_consumption: float
    total_cost: float
    avg_unit_price: float
    currency: str


class Stats(BaseModel):
    total_records: int
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    total_consumption_kwh: Optional[float]
    total_cost: Optional[float]
    currency: Optional[str]


def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> None:
    """
    Verify API key if authentication is enabled.
    Set API_KEY environment variable to enable authentication.
    """
    # If no API_KEY is set, allow all requests (backwards compatible)
    if API_KEY is None:
        return

    # If API_KEY is set, require it in requests
    if api_key is None or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def get_db():
    """Get database connection"""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        raise HTTPException(status_code=500, detail=f"Database not found at {db_path}")
    return duckdb.connect(str(db_path), read_only=True)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Tibber Energy API",
        "version": "1.0.0",
        "endpoints": {
            "hourly": "/api/hourly",
            "daily": "/api/daily",
            "monthly": "/api/monthly",
            "stats": "/api/stats",
            "latest": "/api/latest"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        con = get_db()
        con.execute("SELECT 1").fetchone()
        con.close()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.get("/api/hourly", response_model=List[HourlyConsumption], dependencies=[Depends(verify_api_key)])
async def get_hourly_data(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum number of records")
):
    """Get hourly consumption data"""
    con = get_db()

    query = "SELECT * FROM hourly_consumption WHERE 1=1"
    params = []

    if start_date:
        query += " AND CAST(from_time AS DATE) >= ?"
        params.append(start_date)

    if end_date:
        query += " AND CAST(from_time AS DATE) <= ?"
        params.append(end_date)

    query += " ORDER BY from_time DESC LIMIT ?"
    params.append(limit)

    try:
        result = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily", response_model=List[DailyConsumption], dependencies=[Depends(verify_api_key)])
async def get_daily_data(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(365, ge=1, le=10000, description="Maximum number of records")
):
    """Get daily consumption data"""
    con = get_db()

    query = "SELECT * FROM daily_consumption WHERE 1=1"
    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)

    try:
        result = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monthly", response_model=List[MonthlyConsumption], dependencies=[Depends(verify_api_key)])
async def get_monthly_data(
    year: Optional[int] = Query(None, description="Year (YYYY)"),
    limit: int = Query(24, ge=1, le=1000, description="Maximum number of records")
):
    """Get monthly consumption data"""
    con = get_db()

    query = "SELECT * FROM monthly_consumption WHERE 1=1"
    params = []

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year DESC, month DESC LIMIT ?"
    params.append(limit)

    try:
        result = con.execute(query, params).fetchall()
        columns = [desc[0] for desc in con.description]
        con.close()

        return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=Stats, dependencies=[Depends(verify_api_key)])
async def get_stats():
    """Get overall statistics"""
    con = get_db()

    try:
        result = con.execute("""
            SELECT
                COUNT(*) as total_records,
                MIN(from_time) as date_range_start,
                MAX(from_time) as date_range_end,
                SUM(consumption) as total_consumption_kwh,
                SUM(cost) as total_cost,
                MAX(currency) as currency
            FROM hourly_consumption
        """).fetchone()

        columns = [desc[0] for desc in con.description]
        con.close()

        return dict(zip(columns, result))
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/latest", response_model=HourlyConsumption, dependencies=[Depends(verify_api_key)])
async def get_latest():
    """Get the most recent consumption record"""
    con = get_db()

    try:
        result = con.execute("""
            SELECT * FROM hourly_consumption
            ORDER BY from_time DESC
            LIMIT 1
        """).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="No data found")

        columns = [desc[0] for desc in con.description]
        con.close()

        return dict(zip(columns, result))
    except HTTPException:
        raise
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily/{date}", response_model=DailyConsumption, dependencies=[Depends(verify_api_key)])
async def get_daily_by_date(date: date):
    """Get consumption for a specific date"""
    con = get_db()

    try:
        result = con.execute(
            "SELECT * FROM daily_consumption WHERE date = ?",
            [date]
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for {date}")

        columns = [desc[0] for desc in con.description]
        con.close()

        return dict(zip(columns, result))
    except HTTPException:
        raise
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monthly/{year}/{month}", response_model=MonthlyConsumption, dependencies=[Depends(verify_api_key)])
async def get_monthly_by_year_month(year: int, month: int):
    """Get consumption for a specific month"""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    con = get_db()

    try:
        result = con.execute(
            "SELECT * FROM monthly_consumption WHERE year = ? AND month = ?",
            [year, month]
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"No data found for {year}-{month:02d}")

        columns = [desc[0] for desc in con.description]
        con.close()

        return dict(zip(columns, result))
    except HTTPException:
        raise
    except Exception as e:
        con.close()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
