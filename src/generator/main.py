import logging
import psycopg
import csv
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.config import (
    DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT,
    NUM_USERS, DAYS_OF_DATA, get_db_url_psycopg
)
from src.generator.synthetic_data import SyntheticDataGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def wait_for_db(max_retries: int = 30, retry_delay: int = 1) -> bool:
    """Wait for database to be ready."""
    logger.info(f"Waiting for database at {DB_HOST}:{DB_PORT}...")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg.connect(get_db_url_psycopg())
            conn.close()
            logger.info("✓ Database is ready!")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1}/{max_retries}: Database not ready. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"✗ Failed to connect to database after {max_retries} attempts")
                logger.error(str(e))
                return False
    
    return False


def insert_users(conn: psycopg.Connection, users: list) -> None:
    """Insert user records into database."""
    logger.info(f"Inserting {len(users)} users...")
    
    with conn.cursor() as cur:
        # Disable indexes during bulk insert for speed
        for user in users:
            cur.execute(
                "INSERT INTO users (name, age, gender, device_type) VALUES (%s, %s, %s, %s)",
                (user["name"], user["age"], user["gender"], user["device_type"])
            )
        
        conn.commit()
    
    logger.info(f"✓ Inserted {len(users)} users")


def insert_events_batch(conn: psycopg.Connection, events: list, batch_size: int = 1000) -> None:
    """Insert health metric events in batches."""
    logger.info(f"Inserting {len(events)} events in batches of {batch_size}...")
    
    with conn.cursor() as cur:
        for i in range(0, len(events), batch_size):
            batch = events[i:i+batch_size]
            
            # Prepare data for bulk insert
            for event in batch:
                cur.execute(
                    """
                    INSERT INTO health_metrics (user_id, metric_name, value, time, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        event["user_id"],
                        event["metric_name"].value,
                        event["value"],
                        event["time"],
                        #str(event["metadata"])
                        json.dumps(event["metadata"])
                    )
                )
            
            conn.commit()
            
            if (i + batch_size) % 100000 < batch_size:
                logger.info(f"  Progress: {min(i + batch_size, len(events))}/{len(events)} events inserted")
    
    logger.info(f"✓ Inserted {len(events)} events")


def verify_data(conn: psycopg.Connection) -> None:
    """Verify data was loaded correctly."""
    logger.info("Verifying data integrity...")
    
    with conn.cursor() as cur:
        # Check user count
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        logger.info(f"  Users in DB: {user_count}")
        
        # Check event count
        cur.execute("SELECT COUNT(*) FROM health_metrics")
        event_count = cur.fetchone()[0]
        logger.info(f"  Events in DB: {event_count}")
        
        # Check metrics breakdown
        cur.execute("""
            SELECT metric_name, COUNT(*) as count
            FROM health_metrics
            GROUP BY metric_name
            ORDER BY count DESC
        """)
        logger.info("  Metrics breakdown:")
        for metric, count in cur.fetchall():
            logger.info(f"    {metric}: {count:,}")
        
        # Check date range
        cur.execute("""
            SELECT MIN(time) as earliest, MAX(time) as latest
            FROM health_metrics
        """)
        earliest, latest = cur.fetchone()
        logger.info(f"  Date range: {earliest} to {latest}")
    
    logger.info("✓ Data verification complete")


def main():
    """Main generator orchestration."""
    logger.info("=" * 80)
    logger.info("AI-Queryable Health Data System - Data Generator")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info(f"  Users: {NUM_USERS}")
    logger.info(f"  Days: {DAYS_OF_DATA}")
    logger.info("=" * 80)
    
    # Wait for database
    if not wait_for_db():
        logger.error("Failed to connect to database. Exiting.")
        return 1
    
    try:
        # Connect to database
        conn = psycopg.connect(get_db_url_psycopg())
        logger.info("✓ Connected to database")
        
        # Generate synthetic data
        logger.info("\nGenerating synthetic data...")
        start_time = time.time()
        
        generator = SyntheticDataGenerator(NUM_USERS, DAYS_OF_DATA)
        users, events = generator.generate_population()
        
        gen_time = time.time() - start_time
        logger.info(f"✓ Data generation complete in {gen_time:.2f}s")
        
        # Insert data
        logger.info("\nInserting data into database...")
        insert_time = time.time()
        
        insert_users(conn, users)
        insert_events_batch(conn, events)
        
        insert_time = time.time() - insert_time
        logger.info(f"✓ Data insertion complete in {insert_time:.2f}s")
        
        # Verify data
        logger.info("\nVerifying data...")
        verify_data(conn)
        
        # Close connection
        conn.close()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ Generator completed successfully!")
        logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error(f"✗ Error during generation: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
