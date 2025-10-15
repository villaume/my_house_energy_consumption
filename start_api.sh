#!/bin/bash
# Quick start script for the API

cd "$(dirname "$0")/api"
DATABASE_PATH=../tibber_data.duckdb uvicorn main:app --reload --host 0.0.0.0 --port 8000
