# Load Testing for GremlinsAI Backend - Task T3.5

## Overview

This directory contains comprehensive load testing tools to validate the GremlinsAI Backend's ability to handle **1000+ concurrent users** while maintaining **<2s response times**.

## Acceptance Criteria

✅ **System must maintain <2s response time under load**
✅ **Load test results must meet all performance targets**
✅ **Support 1000+ concurrent users**

## Quick Start

### 1. Install Dependencies

```bash
# Install Locust and required packages
pip install locust>=2.17.0
pip install gevent>=22.10.0
pip install requests>=2.31.0

# Or install from requirements
pip install -r requirements.txt
```

### 2. Start the Application

```bash
# Start the GremlinsAI Backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Verify the application is running
curl http://localhost:8000/
```

### 3. Run Load Test

```bash
# Basic load test (1000 users, default settings)
python scripts/load_testing/run_load_test.py

# Custom configuration
python scripts/load_testing/run_load_test.py \
    --host http://localhost:8000 \
    --users 1000 \
    --spawn-rate 10 \
    --duration 300 \
    --save-results
```

## Test Configuration

### Default Settings

- **Maximum Users**: 1000 concurrent users
- **Spawn Rate**: 10 users per second (100-second ramp-up)
- **Test Duration**: 300 seconds (5 minutes at peak load)
- **Target Host**: http://localhost:8000

### Performance Targets

- **Response Time**: <2.0 seconds (95th percentile)
- **Error Rate**: <5%
- **Throughput**: >100 requests per second

## User Behavior Simulation

The load test simulates realistic user journeys with the following distribution:

### 🎯 **Primary Actions (40%)**
- Starting new conversations
- Asking initial questions
- Testing various query types

### 💬 **Follow-up Questions (25%)**
- Continuing existing conversations
- Maintaining conversation context
- Testing contextual understanding

### 🤖 **Multi-Agent Queries (15%)**
- Complex reasoning tasks
- Research-oriented queries
- Advanced AI capabilities

### 🔍 **System Health Checks (10%)**
- Health endpoint monitoring
- Capabilities checking
- System information requests

### 📚 **Document Operations (5%)**
- RAG queries
- Document searches
- Knowledge retrieval

### 📝 **History Operations (5%)**
- Conversation history access
- Message retrieval
- Context validation

## Command Line Options

```bash
python scripts/load_testing/run_load_test.py [OPTIONS]

Options:
  --host TEXT           Target host URL (default: http://localhost:8000)
  --users INTEGER       Maximum concurrent users (default: 1000)
  --spawn-rate INTEGER  Users to spawn per second (default: 10)
  --duration INTEGER    Test duration in seconds (default: 300)
  --save-results        Save results to JSON file
  --help               Show help message
```

## Example Usage

### Basic Load Test
```bash
# Run with default settings
python scripts/load_testing/run_load_test.py
```

### Staging Environment Test
```bash
# Test against staging environment
python scripts/load_testing/run_load_test.py \
    --host https://staging.gremlinsai.com \
    --users 1500 \
    --spawn-rate 15 \
    --duration 600 \
    --save-results
```

### Quick Performance Check
```bash
# Smaller test for quick validation
python scripts/load_testing/run_load_test.py \
    --users 100 \
    --spawn-rate 5 \
    --duration 60
```

### High-Load Stress Test
```bash
# Stress test with higher load
python scripts/load_testing/run_load_test.py \
    --users 2000 \
    --spawn-rate 20 \
    --duration 900 \
    --save-results
```

## Test Results

### Sample Output

```
🚀 Starting Load Test
   Target: 1000 concurrent users
   Spawn rate: 10 users/second
   Duration: 300 seconds
   Host: http://localhost:8000

⏳ Ramping up to 1000 users (100.0s)...
✅ Ramp-up complete: 1000 users active

🔥 Running at peak load for 300 seconds...
   Time: 0s | RPS: 245.3 | Avg Response: 1247ms | Error Rate: 0.12%
   Time: 30s | RPS: 312.7 | Avg Response: 1156ms | Error Rate: 0.08%
   Time: 60s | RPS: 298.4 | Avg Response: 1203ms | Error Rate: 0.05%

🏁 Load test completed!

================================================================================
📊 LOAD TEST RESULTS - Task T3.5
================================================================================

📋 Test Summary:
   Host: http://localhost:8000
   Concurrent Users: 1,000
   Test Duration: 400.1 seconds
   Total Requests: 125,847
   Total Failures: 63

📈 Performance Metrics:
   Requests/Second: 314.5
   Average Response Time: 1.187s
   50th Percentile: 0.892s
   95th Percentile: 1.743s
   99th Percentile: 2.156s
   Max Response Time: 3.247s
   Error Rate: 0.05%

✅ Acceptance Criteria Validation:
   Response Time (<2.0s): ✅ PASS
      95th Percentile: 1.743s
   Error Rate (<5.0%): ✅ PASS
      Actual: 0.05%
   Throughput (>100 RPS): ✅ PASS
      Actual: 314.5 RPS

🎯 Overall Result: 🎉 PASS
   ✅ System meets all performance requirements for 1000+ concurrent users
   ✅ Ready for production deployment
```

### Results Storage

When using `--save-results`, test results are saved to:
```
scripts/load_testing/results/load_test_results_YYYYMMDD_HHMMSS.json
```

The JSON file contains:
- Test summary and configuration
- Detailed performance metrics
- Acceptance criteria validation
- Request-level statistics

## Monitoring Integration

### Prometheus Metrics

During load testing, monitor these key metrics:

```promql
# API Request Rate
sum(rate(gremlinsai_api_requests_total[1m]))

# Response Time (95th percentile)
histogram_quantile(0.95, rate(gremlinsai_api_request_duration_seconds_bucket[1m]))

# Error Rate
sum(rate(gremlinsai_api_errors_total[1m])) / sum(rate(gremlinsai_api_requests_total[1m]))

# Active Conversations
gremlinsai_active_conversations

# Memory Usage
gremlinsai_memory_usage_bytes{component="application"}
```

### Grafana Dashboard

Use the GremlinsAI monitoring dashboard to observe:
- Real-time request rates and response times
- Error rates and failure patterns
- System resource utilization
- LLM provider performance
- Agent tool success rates

## Troubleshooting

### Common Issues

#### High Response Times
```bash
# Check system resources
htop
iostat -x 1

# Monitor database connections
# Check application logs for bottlenecks
```

#### High Error Rates
```bash
# Check application logs
tail -f logs/app.log

# Verify all services are running
curl http://localhost:8000/api/v1/health/health

# Check database connectivity
```

#### Low Throughput
```bash
# Increase worker processes
uvicorn app.main:app --workers 4

# Check for resource constraints
# Monitor CPU and memory usage
```

### Performance Optimization

#### Application Level
- Increase worker processes/threads
- Optimize database queries
- Implement connection pooling
- Add caching layers

#### Infrastructure Level
- Scale horizontally with load balancers
- Increase server resources (CPU/RAM)
- Optimize database configuration
- Use CDN for static content

#### Code Level
- Profile slow endpoints
- Optimize LLM provider calls
- Implement async processing
- Add request queuing

## Advanced Usage

### Custom User Behavior

Modify `GremlinsAIUser` class to add custom user behaviors:

```python
@task(10)  # 10% of requests
def custom_behavior(self):
    """Add your custom user behavior here."""
    # Custom API calls
    # Specific test scenarios
    # Edge case testing
```

### Environment-Specific Testing

Create environment-specific configurations:

```python
# Production-like test
python scripts/load_testing/run_load_test.py \
    --host https://api.gremlinsai.com \
    --users 5000 \
    --spawn-rate 50 \
    --duration 1800
```

### Continuous Integration

Integrate with CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Load Tests
  run: |
    python scripts/load_testing/run_load_test.py \
      --users 500 \
      --duration 180 \
      --save-results
    
    # Fail build if performance targets not met
    if [ $? -ne 0 ]; then
      echo "Load test failed - performance targets not met"
      exit 1
    fi
```

## Performance Benchmarks

### Target Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Concurrent Users** | 1000+ | Sustained load |
| **Response Time** | <2.0s | 95th percentile |
| **Error Rate** | <5% | Failed requests |
| **Throughput** | >100 RPS | Requests per second |

### Expected Results

For a properly configured system:

- **Ramp-up**: Smooth increase to 1000 users over ~100 seconds
- **Sustained Load**: Stable performance for 5+ minutes
- **Response Times**: 95th percentile under 2 seconds
- **Error Rate**: Less than 1% under normal conditions
- **Throughput**: 200-500 RPS depending on query complexity

## Support

### Getting Help

1. **Check Application Logs**: Look for errors or performance issues
2. **Monitor System Resources**: CPU, memory, disk, network usage
3. **Review Test Configuration**: Ensure appropriate test parameters
4. **Validate Environment**: Confirm all services are running properly

### Reporting Issues

When reporting performance issues, include:
- Load test configuration used
- Complete test results output
- System resource utilization
- Application logs during test
- Environment details (OS, Python version, etc.)

## Summary

This load testing framework provides comprehensive validation of the GremlinsAI Backend's performance under realistic load conditions. It ensures the system meets the critical requirement of supporting 1000+ concurrent users while maintaining sub-2-second response times.

**Key Features:**
- ✅ Realistic user behavior simulation
- ✅ Gradual ramp-up to target load
- ✅ Automatic acceptance criteria validation
- ✅ Comprehensive performance reporting
- ✅ Integration with monitoring stack
- ✅ Production-ready test scenarios

Run the load tests regularly to ensure continued performance as the system evolves and scales.
