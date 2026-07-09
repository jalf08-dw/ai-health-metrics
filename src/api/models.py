from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class MetricType(str, Enum):
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_STAGE = "sleep_stage"
    BLOOD_OXYGEN = "blood_oxygen"
    WORKOUT_DURATION = "workout_duration"


class AggregationType(str, Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    SUM = "sum"
    STDDEV = "stddev"


class User(BaseModel):
    user_id: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    device_type: Optional[str] = None
    created_at: datetime


class HealthMetric(BaseModel):
    user_id: int
    metric_name: MetricType
    value: float
    time: datetime
    metadata: Optional[Dict[str, Any]] = None


class MetricsQueryRequest(BaseModel):
    user_id: int = Field(..., description="User ID to query")
    metric: MetricType = Field(..., description="Health metric to retrieve")
    days: int = Field(default=7, ge=1, le=90, description="Number of days to look back")
    aggregation: Optional[AggregationType] = Field(None, description="Aggregation type (optional)")
    bucket_hours: Optional[int] = Field(None, ge=1, le=24, description="Time bucket in hours for aggregation")


class MetricsQueryResponse(BaseModel):
    user_id: int
    metric: MetricType
    data_points: int
    date_range: Dict[str, datetime]
    aggregation: Optional[str] = None
    results: List[Dict[str, Any]]
    query_time_ms: float


class NLQueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about health data")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")


class NLQueryResponse(BaseModel):
    question: str
    generated_sql: Optional[str] = None
    results: List[Dict[str, Any]]
    explanation: Optional[str] = None
    error: Optional[str] = None
    query_time_ms: float


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
