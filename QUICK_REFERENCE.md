# Quick Reference

## Essential Commands

```bash
# Start everything
docker compose up

# View logs
docker compose logs -f api

# Stop services
docker compose down

# Run tests
pytest tests/ -v

# Open API documentation
open http://localhost:8000/docs

# Connect to database
docker exec -it health-metrics-db psql -U postgres -d health_metrics
```

## Common Queries

### Get User Data
```bash
curl http://localhost:8000/api/users/1
```

### Query Heart Rate (Last 7 Days)
```bash
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "metric": "heart_rate",
    "days": 7
  }'
```

### Aggregated Stats
```bash
curl "http://localhost:8000/api/metrics/1/stats?metric=heart_rate&days=7"
```

### Daily Summary
```bash
curl "http://localhost:8000/api/metrics/1/daily-summary?days=7"
```

### Natural Language Query
```bash
curl -X POST http://localhost:8000/api/nl-query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was my average heart rate last week?"
  }'
```

### Custom SQL
```bash
curl -X POST "http://localhost:8000/api/query?sql=SELECT%20COUNT(*)%20FROM%20health_metrics%20LIMIT%201000"
```

## Database Access

### Direct SQL Connection
```bash
# From host (if psql installed)
psql -h localhost -U postgres -d health_metrics

# From Docker
docker exec -it health-metrics-db psql -U postgres -d health_metrics
```

### Useful SQL Queries
```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check hypertable info
SELECT * FROM timescaledb_information.hypertables;

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'health_metrics';

-- Sample data
SELECT * FROM health_metrics LIMIT 10;

-- Check data volume
SELECT metric_name, COUNT(*) FROM health_metrics GROUP BY metric_name;
```

## Troubleshooting

### Generator Is Slow
- Expected: 2-5 minutes first run
- Check logs: `docker logs health-metrics-generator`
- Speed up for testing: Edit `.env`, set `NUM_USERS=10`, `DAYS_OF_DATA=5`

### API Won't Connect to Database
```bash
# Check if database is healthy
docker exec health-metrics-db pg_isready -U postgres

# Check logs
docker logs health-metrics-db

# Wait a few seconds and try again (DB needs time to start)
```

### Port Already in Use
```bash
# Port 5432 (PostgreSQL)
lsof -i :5432  # Find process
kill -9 <PID>  # Kill process

# Port 8000 (API)
lsof -i :8000
kill -9 <PID>
```

## Development

### Enable Natural Language Layer
1. Get API key: https://console.anthropic.com/account/keys
2. Edit `.env`: `OPENAI_API_KEY=sk-ant-...`
3. Restart API: `docker compose restart api`

### Add More Test Data
Edit `.env`:
```
NUM_USERS=500       # Default: 100
DAYS_OF_DATA=90     # Default: 30
```

Then restart: `docker compose down && docker compose up`

### Run Tests Locally
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pytest tests/ -v --tb=short
```

### Debug API
```bash
# Run with auto-reload
uvicorn src.api.main:app --reload --log-level debug

# Or in Docker
docker logs -f health-metrics-api
```

## Performance Tuning

### Check Query Plans
```sql
EXPLAIN ANALYZE
SELECT AVG(value) FROM health_metrics 
WHERE user_id = 1 AND metric_name = 'heart_rate'
AND time > NOW() - INTERVAL '7 days';
```

### Verify Indexes Are Used
Look for "Index Scan" or "Index Cond" in output

### Manual Compression
```sql
-- Compress specific chunks
SELECT compress_chunk(chunk) 
FROM timescaledb_information.chunks 
WHERE hypertable_name = 'health_metrics';
```

## Useful Links

- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI:** http://localhost:8000/openapi.json
- **TimescaleDB Docs:** https://docs.timescale.com/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Anthropic API:** https://console.anthropic.com/

## File Changes

To modify:

| What | File | Impact |
|------|------|--------|
| Database config | `src/shared/config.py` | Affects both generator and API |
| Data generation | `src/generator/synthetic_data.py` | Restart generator to regenerate |
| API endpoints | `src/api/main.py` | Restart API to apply |
| Schema | `schema/init.sql` | Requires `docker compose down -v` and restart |
| Dependencies | `src/*/requirements.txt` | Rebuild Docker images |

## Check System Status

```bash
# All services healthy?
curl http://localhost:8000/status

# Database connected?
curl http://localhost:8000/health

# How many users?
curl http://localhost:8000/api/users | jq '.count'

# How much data?
curl -X POST 'http://localhost:8000/api/query?sql=SELECT%20COUNT(*)%20FROM%20health_metrics%20LIMIT%201000'
```

---

For detailed information, see README.md
