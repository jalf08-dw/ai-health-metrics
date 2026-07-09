import psycopg
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseQueries:
    """Database query operations."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def get_connection(self) -> psycopg.Connection:
        """Get database connection."""
        return psycopg.connect(self.db_url)
    
    def health_check(self) -> Tuple[bool, str]:
        """Check database connectivity."""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            return True, "Database connected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False, str(e)
    
    def get_all_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all users (with limit)."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, name, age, gender, device_type, created_at FROM users LIMIT %s",
                    (limit,)
                )
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get specific user."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, name, age, gender, device_type, created_at FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
                return None
        finally:
            conn.close()
    
    def get_metrics(
        self,
        user_id: int,
        metric_name: str,
        days: int = 7,
        aggregation: Optional[str] = None,
        bucket_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get health metrics for user with optional aggregation."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                
                if aggregation and bucket_hours:
                    # Time-bucketed aggregation (fast with TimescaleDB)
                    sql = f"""
                    SELECT
                        time_bucket('{bucket_hours} hours', time) AS bucket,
                        COUNT(*) as sample_count,
                        AVG(value) as avg_value,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        STDDEV(value) as stddev_value
                    FROM health_metrics
                    WHERE user_id = %s
                        AND metric_name = %s
                        AND time >= %s
                        AND time <= %s
                    GROUP BY bucket
                    ORDER BY bucket DESC
                    LIMIT 1000
                    """
                    cur.execute(sql, (user_id, metric_name, start_time, end_time))
                else:
                    # Raw data
                    sql = """
                    SELECT
                        time,
                        value,
                        metadata
                    FROM health_metrics
                    WHERE user_id = %s
                        AND metric_name = %s
                        AND time >= %s
                        AND time <= %s
                    ORDER BY time DESC
                    LIMIT 10000
                    """
                    cur.execute(sql, (user_id, metric_name, start_time, end_time))
                
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
    
    def get_metrics_stats(self, user_id: int, metric_name: str, days: int = 7) -> Dict[str, Any]:
        """Get aggregated statistics for a metric."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                
                sql = """
                SELECT
                    COUNT(*) as sample_count,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    STDDEV(value) as stddev_value,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_value
                FROM health_metrics
                WHERE user_id = %s
                    AND metric_name = %s
                    AND time >= %s
                    AND time <= %s
                """
                cur.execute(sql, (user_id, metric_name, start_time, end_time))
                
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
                return {}
        finally:
            conn.close()
    
    def execute_custom_sql(self, sql: str, limit: int = 1000) -> Tuple[List[Dict[str, Any]], int]:
        """Execute custom SQL query (with safety checks)."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Add LIMIT if not present (safety)
                if "LIMIT" not in sql.upper():
                    sql = sql.rstrip(';') + f" LIMIT {limit}"
                
                cur.execute(sql)
                
                # Check if there are results
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    results = [dict(zip(columns, row)) for row in rows]
                    return results, len(results)
                return [], 0
        finally:
            conn.close()
    
    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL query syntax (without executing)."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Use EXPLAIN to validate without executing
                cur.execute(f"EXPLAIN {sql}")
            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
    
    def get_user_daily_summary(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily summary for all metrics."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days)
                
                sql = """
                SELECT
                    time_bucket('1 day', time) as day,
                    metric_name,
                    COUNT(*) as sample_count,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value
                FROM health_metrics
                WHERE user_id = %s
                    AND time >= %s
                    AND time <= %s
                GROUP BY day, metric_name
                ORDER BY day DESC, metric_name
                """
                cur.execute(sql, (user_id, start_time, end_time))
                
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
    
    def search_users(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search users by name or device."""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                search_term = f"%{query}%"
                sql = """
                SELECT user_id, name, age, gender, device_type, created_at
                FROM users
                WHERE name ILIKE %s OR device_type ILIKE %s
                LIMIT %s
                """
                cur.execute(sql, (search_term, search_term, limit))
                
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
