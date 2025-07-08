# Database Connection Management Guide

## Overview

This guide explains the PostgreSQL connection limit issue and provides solutions to prevent the "too many clients already" error.

## The Problem

PostgreSQL connections are exhausted when the total number of active connections exceeds the server's `max_connections` setting. In this system:

```
django.db.utils.OperationalError: connection to server at "postgres" (172.18.0.2), port 5432 failed: 
FATAL: sorry, too many clients already
```

### Root Causes
1. **Multiple services** connecting to the same PostgreSQL instance
2. **Connection leaks** from long-running operations
3. **Insufficient connection pool management**
4. **Default PostgreSQL limits** being too low for the workload

## Current Configuration

### PostgreSQL Server Limits
- **max_connections**: 200 (configured in docker-compose.yml)
- **shared_buffers**: 128MB
- **effective_cache_size**: 512MB

### Django Connection Pool Settings

#### Local Development
- **MAX_CONNS**: 20 per Django process (configurable via `DB_MAX_CONNS`)
- **CONN_MAX_AGE**: 300 seconds (5 minutes)

#### Production
- **MAX_CONNS**: 50 per Django process (configurable via `DB_MAX_CONNS`)
- **CONN_MAX_AGE**: 600 seconds (10 minutes)

## Enhanced Solutions Implemented

### 1. Improved Database Configuration

#### Configurable Connection Limits
```bash
# Environment variable to control connection pool size
export DB_MAX_CONNS=25  # Adjust based on service needs
```

#### Connection Reliability Settings
- **Keepalive mechanisms** to detect stale connections
- **Connection timeouts** to prevent hanging connections
- **Application naming** for better monitoring

### 2. Advanced Monitoring Tools

#### Database Connection Management Command
```bash
# Check current connection status
python manage.py db_connections --action=status

# Comprehensive health check
python manage.py db_connections --action=health

# Close idle connections
python manage.py db_connections --action=close-idle

# Continuous monitoring
python manage.py db_connections --action=monitor --watch --interval=5
Idle Connections: 33
Utilization: 22.5%
✅ Connection utilization is healthy

=== Connections by Application ===
wall-django-api: 15 connections (active, idle)
wall-django-materializer: 12 connections (active, idle)
psql: 1 connections (active)
```

#### Connection Monitoring in Application Code
```python
from apps.common.db_utils import connection_monitor, check_connection_health

# Monitor connections during operations
with connection_monitor("bulk_operation"):
    # Your database operations here
    process_large_dataset()

# Check connection health
health = check_connection_health()
if health['postgresql_info']['utilization_percent'] > 90:
    logger.warning("High connection utilization detected")
```

### 3. Optimized PostgreSQL Configuration

#### Recommended Server Settings
```yaml
# docker-compose.yml
postgres:
  command: >
    postgres
    -c max_connections=400              # Increased capacity
    -c shared_buffers=256MB            # Better memory usage
    -c effective_cache_size=1GB        # Improved caching
    -c maintenance_work_mem=128MB      # Better maintenance
    # Connection management
    -c idle_in_transaction_session_timeout=300000  # 5 minutes
    -c tcp_keepalives_idle=600         # 10 minutes
    -c tcp_keepalives_interval=30      # 30 seconds
    -c tcp_keepalives_count=3          # 3 retries
```

### 4. Connection Pool Calculation

**Total connection usage estimation**:
- API service: 4 workers × 25 connections = 100 connections
- Materializer: 1 process × 25 connections = 25 connections  
- Simulator: 1 process × 25 connections = 25 connections
- Admin/monitoring: ~10 connections
- **Total**: ~160 connections (safe under 200 limit)

## Implementation Steps

### Immediate Actions (Zero Downtime)

1. **Monitor current usage**:
```bash
python manage.py db_connections --action=health
```

2. **Adjust connection pools**:
```bash
# For API service
export DB_MAX_CONNS=25

# For materializer
export DB_MAX_CONNS=20
```

3. **Close idle connections**:
```bash
python manage.py db_connections --action=close-idle
```

### Short-term Improvements

1. **Update docker-compose.yml**:
```yaml
postgres:
  command: >
    postgres
    -c max_connections=400
    -c shared_buffers=256MB
```

2. **Add monitoring alerts**:
```python
# In your monitoring system
def check_db_connections():
    health = check_connection_health()
    if health['postgresql_info']['utilization_percent'] > 80:
        send_alert("High database connection utilization")
```

### Long-term Solutions

1. **Implement PgBouncer** for connection pooling
2. **Add read replicas** for read-heavy operations  
3. **Implement connection-aware load balancing**
4. **Consider connection pooling middleware**

## Troubleshooting Guide

### Common Scenarios

#### 1. "Too many clients already" Error
```bash
# Step 1: Check current status
python manage.py db_connections --action=health

# Step 2: Close idle connections
python manage.py db_connections --action=close-idle

# Step 3: Reduce pool size temporarily
export DB_MAX_CONNS=15
docker-compose restart api materializer

# Step 4: Monitor recovery
python manage.py db_connections --action=monitor --watch
```

#### 2. High Idle Connection Count
```bash
# Check connection details
python manage.py db_connections --action=status

# Reduce connection lifetime
# In settings: CONN_MAX_AGE = 180  # 3 minutes
```

#### 3. Connection Leaks
```bash
# Force close all Django connections
python manage.py db_connections --action=force-close

# Restart services
docker-compose restart api materializer
```

### Emergency Procedures

1. **Immediate relief**:
```sql
-- Connect to PostgreSQL directly
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'wall' 
  AND state = 'idle' 
  AND state_change < now() - interval '5 minutes';
```

2. **Temporary limit increase**:
```sql
-- Increase limit temporarily (requires restart)
ALTER SYSTEM SET max_connections = 500;
SELECT pg_reload_conf();
```

## Environment Configuration

### Development
```env
DB_MAX_CONNS=10          # Low usage
CONN_MAX_AGE=180         # 3 minutes
DEBUG=true
```

### Staging
```env
DB_MAX_CONNS=20          # Moderate usage
CONN_MAX_AGE=300         # 5 minutes
DEBUG=false
```

### Production
```env
DB_MAX_CONNS=25          # High usage
CONN_MAX_AGE=600         # 10 minutes
DEBUG=false
```

### High-Load Production
```env
DB_MAX_CONNS=15          # More workers, fewer connections each
CONN_MAX_AGE=300         # Shorter lifetime
# Consider PgBouncer
```

## Monitoring and Alerting

### Key Metrics

1. **Connection utilization**: Target < 70%, Alert > 85%
2. **Idle connection ratio**: Alert if > 50% of connections idle
3. **Connection churn rate**: Monitor connection creates/destroys
4. **Query duration**: Long-running queries hold connections

### Automated Monitoring
```python
# Add to your monitoring system
def monitor_db_connections():
    health = check_connection_health()
    metrics = health['postgresql_info']
    
    # Alert thresholds
    if metrics['utilization_percent'] > 85:
        alert_critical("Database connection utilization critical")
    elif metrics['utilization_percent'] > 70:
        alert_warning("Database connection utilization high")
    
    # Log for trending
    log_metric("db.connections.total", metrics['total_connections'])
    log_metric("db.connections.utilization", metrics['utilization_percent'])
```

## Best Practices

1. **Always monitor** connection usage in production
2. **Use connection context managers** for long operations
3. **Configure appropriate timeouts** for all connection settings
4. **Implement graceful shutdown** with connection cleanup
5. **Batch operations efficiently** to minimize connection time
6. **Consider read replicas** for read-heavy workloads
7. **Use prepared statements** for frequently executed queries
8. **Implement circuit breakers** for database operations

## Performance Impact

### Connection Pool Sizing Impact

| Pool Size | Throughput | Latency | Resource Usage |
|-----------|------------|---------|----------------|
| 10        | Lower      | Higher  | Low Memory     |
| 25        | Optimal    | Low     | Balanced       |
| 50        | Higher     | Low     | High Memory    |
| 100+      | Diminishing| Low     | Very High      |

### Optimization Guidelines

1. **Start conservative**: Begin with smaller pool sizes
2. **Monitor and adjust**: Increase based on actual usage
3. **Consider worker count**: More workers = smaller pools per worker
4. **Test under load**: Validate configuration with realistic traffic

## Future Improvements

### Planned Enhancements

1. **Connection pooling middleware** (PgBouncer integration)
2. **Read/write splitting** for better resource utilization
3. **Connection-aware load balancing**
4. **Advanced connection health checks**
5. **Automated connection pool scaling**

### Architecture Considerations

1. **Service mesh integration** for connection management
2. **Database proxy layer** for advanced pooling
3. **Multi-region database setup** with connection affinity
4. **Container-based connection limits** tied to resource allocation

## References

- [PostgreSQL Connection Management](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Django Database Connections](https://docs.djangoproject.com/en/stable/ref/databases/#connection-management)
- [PgBouncer Documentation](https://pgbouncer.github.io/)
- [Connection Pool Sizing Best Practices](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)
