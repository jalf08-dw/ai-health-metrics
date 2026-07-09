import logging
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.config import (
    get_db_url_psycopg, API_TITLE, API_VERSION, API_DESCRIPTION
)
from src.api.models import (
    MetricsQueryRequest, MetricsQueryResponse,
    NLQueryRequest, NLQueryResponse,
    HealthCheckResponse, User, MetricType
)
from src.api.queries import DatabaseQueries
from src.api.nl_layer import nl_layer

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database queries
db = DatabaseQueries(get_db_url_psycopg())


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse, tags=["Status"])
async def health_check():
    """Health check endpoint for Docker healthchecks."""
    is_healthy, message = db.health_check()
    
    if not is_healthy:
        raise HTTPException(status_code=503, detail=message)
    
    return HealthCheckResponse(
        status="healthy",
        database="connected",
        timestamp=datetime.now()
    )


@app.get("/status", tags=["Status"])
async def status():
    """Get system status and NL layer availability."""
    is_healthy, db_message = db.health_check()
    
    return {
        "status": "operational" if is_healthy else "degraded",
        "database": {
            "status": "connected" if is_healthy else "disconnected",
            "message": db_message
        },
        "nl_layer": {
            "available": nl_layer.is_available(),
            "message": "Claude API configured" if nl_layer.is_available() else "Claude API not configured"
        },
        "timestamp": datetime.now()
    }


# ============================================================================
# User Endpoints
# ============================================================================

@app.get("/api/users", response_model=dict, tags=["Users"])
async def list_users(limit: int = Query(100, ge=1, le=1000)):
    """List all users."""
    try:
        users = db.get_all_users(limit=limit)
        return {
            "count": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_id}", response_model=User, tags=["Users"])
async def get_user(user_id: int):
    """Get specific user by ID."""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return user
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/search", response_model=dict, tags=["Users"])
async def search_users(q: str = Query(..., min_length=1, max_length=100)):
    """Search users by name or device."""
    try:
        results = db.search_users(q, limit=20)
        return {
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Metrics Endpoints
# ============================================================================

@app.post("/api/metrics", response_model=MetricsQueryResponse, tags=["Metrics"])
async def query_metrics(request: MetricsQueryRequest):
    """Query health metrics for a user with optional aggregation."""
    start_time = time.time()
    
    try:
        # Validate user exists
        user = db.get_user_by_id(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
        
        # Get metrics
        results = db.get_metrics(
            user_id=request.user_id,
            metric_name=request.metric.value,
            days=request.days,
            aggregation=request.aggregation.value if request.aggregation else None,
            bucket_hours=request.bucket_hours
        )
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return MetricsQueryResponse(
            user_id=request.user_id,
            metric=request.metric,
            data_points=len(results),
            date_range={
                "start": datetime.now() - __import__('datetime').timedelta(days=request.days),
                "end": datetime.now()
            },
            aggregation=request.aggregation.value if request.aggregation else None,
            results=results,
            query_time_ms=query_time_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/{user_id}/stats", response_model=dict, tags=["Metrics"])
async def get_metrics_stats(
    user_id: int,
    metric: MetricType = Query(...),
    days: int = Query(7, ge=1, le=90)
):
    """Get aggregated statistics for a metric."""
    start_time = time.time()
    
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        stats = db.get_metrics_stats(user_id, metric.value, days)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return {
            "user_id": user_id,
            "metric": metric.value,
            "days": days,
            "stats": stats,
            "query_time_ms": query_time_ms
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/{user_id}/daily-summary", response_model=dict, tags=["Metrics"])
async def get_daily_summary(
    user_id: int,
    days: int = Query(7, ge=1, le=90)
):
    """Get daily summary for all metrics."""
    start_time = time.time()
    
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        summary = db.get_user_daily_summary(user_id, days)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return {
            "user_id": user_id,
            "days": days,
            "data_points": len(summary),
            "summary": summary,
            "query_time_ms": query_time_ms
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Query Endpoints
# ============================================================================

@app.post("/api/query", response_model=dict, tags=["Query"])
async def execute_query(
    sql: str = Query(..., min_length=5, max_length=5000)
):
    """Execute custom SQL query (READ-ONLY)."""
    start_time = time.time()
    
    try:
        # Validate query
        is_valid, error = db.validate_sql(sql)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid SQL: {error}")
        
        # Execute query
        results, count = db.execute_custom_sql(sql)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return {
            "sql": sql,
            "row_count": count,
            "results": results,
            "query_time_ms": query_time_ms
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Natural Language Query Endpoint (Bonus 2)
# ============================================================================

@app.post("/api/nl-query", response_model=NLQueryResponse, tags=["Natural Language"])
async def natural_language_query(request: NLQueryRequest):
    """Query health data using natural language."""
    start_time = time.time()
    
    try:
        if not nl_layer.is_available():
            raise HTTPException(
                status_code=503,
                detail="Natural language layer not available. Set OPENAI_API_KEY."
            )
        
        # Generate SQL from natural language
        generated_sql, nl_error = nl_layer.generate_sql(request.question)
        
        if nl_error:
            return NLQueryResponse(
                question=request.question,
                generated_sql=None,
                results=[],
                explanation=None,
                error=nl_error,
                query_time_ms=(time.time() - start_time) * 1000
            )
        
        # Execute generated SQL
        results, count = db.execute_custom_sql(generated_sql, limit=request.max_results)
        
        # Generate explanation
        explanation = nl_layer.explain_question(request.question)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return NLQueryResponse(
            question=request.question,
            generated_sql=generated_sql,
            results=results,
            explanation=explanation,
            error=None,
            query_time_ms=query_time_ms
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in NL query: {e}")
        return NLQueryResponse(
            question=request.question,
            generated_sql=None,
            results=[],
            explanation=None,
            error=str(e),
            query_time_ms=(time.time() - start_time) * 1000
        )


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Status"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "users": "/api/users",
            "metrics": "/api/metrics",
            "query": "/api/query",
            "nl_query": "/api/nl-query"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
