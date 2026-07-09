import logging
import json
import re
from typing import Optional, Tuple, List
from src.shared.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class NaturalLanguageLayer:
    """Convert natural language questions to SQL queries."""
    
    # Safe columns that can be accessed
    ALLOWED_COLUMNS = {
        'user_id', 'metric_name', 'value', 'time', 'metadata',
        'name', 'age', 'gender', 'device_type', 'created_at'
    }
    
    ALLOWED_TABLES = {'health_metrics', 'users', 'daily_user_stats'}
    
    METRIC_NAMES = {
        'heart_rate', 'steps', 'sleep_duration', 'sleep_stage',
        'blood_oxygen', 'workout_duration'
    }
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.available = bool(self.api_key)
        
        if not self.available:
            logger.warning("Natural language layer disabled: OPENAI_API_KEY not set")
    
    def is_available(self) -> bool:
        """Check if NL layer is available."""
        return self.available
    
    def generate_sql(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """Convert natural language question to SQL."""
        if not self.available:
            return None, "Natural language layer not configured. Set OPENAI_API_KEY."
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            system_prompt = """You are a database expert that converts natural language questions into SQL.

You have access to these tables:
- health_metrics: (id, user_id, metric_name, value, time, metadata)
  - metric_name: 'heart_rate', 'steps', 'sleep_duration', 'sleep_stage', 'blood_oxygen', 'workout_duration'
  - This is a TimescaleDB hypertable with time-series data
- users: (user_id, name, age, gender, device_type, created_at)

Generate ONLY the SQL query, nothing else. Use TimescaleDB functions like time_bucket() for time series.
Examples:
- "average heart rate last week" -> SELECT AVG(value) FROM health_metrics WHERE metric_name = 'heart_rate' AND time > NOW() - INTERVAL '7 days'
- "steps today" -> SELECT SUM(value) FROM health_metrics WHERE metric_name = 'steps' AND DATE(time) = CURRENT_DATE
- "which users had the most workouts" -> SELECT user_id, COUNT(*) FROM health_metrics WHERE metric_name = 'workout_duration' GROUP BY user_id ORDER BY COUNT(*) DESC

Always include LIMIT 1000 at the end."""

            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": f"Convert this question to SQL: {question}"
                    }
                ],
                system=system_prompt
            )
            
            sql = message.content[0].text.strip()
            
            # Validation
            is_valid, error = self._validate_sql_safety(sql)
            if not is_valid:
                return None, f"Generated SQL failed validation: {error}"
            
            return sql, None
            
        except ImportError:
            return None, "anthropic library not installed. Run: pip install anthropic"
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return None, f"Error generating SQL: {str(e)}"
    
    def _validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL for safety."""
        sql_upper = sql.upper()
        
        # Block dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'MODIFY', 'INSERT', 'UPDATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Query contains dangerous keyword: {keyword}"
        
        # Ensure only SELECT
        if not sql_upper.strip().startswith('SELECT'):
            return False, "Only SELECT queries allowed"
        
        # Check for obvious injection patterns
        if "';--" in sql or '";"' in sql or '/*' in sql:
            return False, "Query contains potential injection patterns"
        
        # Ensure LIMIT is present
        if 'LIMIT' not in sql_upper:
            return False, "Query must include LIMIT clause"
        
        return True, None
    
    def explain_question(self, question: str) -> Optional[str]:
        """Generate explanation of the question's interpretation."""
        if not self.available:
            return None
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": f"In one sentence, explain what this health data question is asking for: '{question}'"
                    }
                ]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Error explaining question: {e}")
            return None


# Global NL layer instance
nl_layer = NaturalLanguageLayer()
