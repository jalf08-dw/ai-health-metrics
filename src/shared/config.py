import os
import logging
from typing import Optional

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "health_metrics")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

# Data Generation Configuration
NUM_USERS = int(os.getenv("NUM_USERS", "100"))
DAYS_OF_DATA = int(os.getenv("DAYS_OF_DATA", "30"))

# API Configuration
API_TITLE = "Health Metrics API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "AI-Queryable Health Data System with Natural Language Support"

# OpenAI Configuration (optional, for NL layer)
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_db_url() -> str:
    """Build PostgreSQL connection string"""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_url_psycopg() -> str:
    """Build psycopg3 connection string"""
    return f"host={DB_HOST} user={DB_USER} password={DB_PASSWORD} dbname={DB_NAME} port={DB_PORT}"
