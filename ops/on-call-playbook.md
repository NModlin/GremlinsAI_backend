# GremlinsAI Production On-Call Playbook - Task T3.8

## Overview

This playbook provides comprehensive incident response procedures for the GremlinsAI Backend production environment. It establishes 24/7 monitoring with on-call rotation and detailed response protocols.

## 📞 On-Call Rotation & Contacts

### Current On-Call Schedule

| Week | Primary On-Call | Secondary On-Call | Escalation Manager |
|------|----------------|-------------------|-------------------|
| Week 1 | Alex Chen | Sarah Johnson | Mike Rodriguez |
| Week 2 | Sarah Johnson | David Kim | Mike Rodriguez |
| Week 3 | David Kim | Alex Chen | Lisa Wang |
| Week 4 | Alex Chen | Sarah Johnson | Lisa Wang |

### Contact Information

#### Primary On-Call Engineers
- **Alex Chen** (Platform Team Lead)
  - Phone: +1-555-0101
  - Slack: @alex.chen
  - Email: alex.chen@company.com
  - Timezone: PST (UTC-8)

- **Sarah Johnson** (AI Platform Engineer)
  - Phone: +1-555-0102
  - Slack: @sarah.johnson
  - Email: sarah.johnson@company.com
  - Timezone: EST (UTC-5)

- **David Kim** (Infrastructure Engineer)
  - Phone: +1-555-0103
  - Slack: @david.kim
  - Email: david.kim@company.com
  - Timezone: CST (UTC-6)

#### Escalation Contacts
- **Mike Rodriguez** (Engineering Manager)
  - Phone: +1-555-0201
  - Slack: @mike.rodriguez
  - Email: mike.rodriguez@company.com

- **Lisa Wang** (VP Engineering)
  - Phone: +1-555-0301
  - Slack: @lisa.wang
  - Email: lisa.wang@company.com

#### Subject Matter Experts
- **Database Issues**: David Kim, Alex Chen
- **LLM/AI Issues**: Sarah Johnson, Dr. Emily Zhang
- **Weaviate/Vector DB**: Sarah Johnson, Alex Chen
- **Kubernetes/Infrastructure**: David Kim, Mike Rodriguez

### On-Call Responsibilities

#### Primary On-Call
- Respond to critical alerts within **5 minutes**
- Acknowledge alerts in PagerDuty within **2 minutes**
- Begin investigation and mitigation immediately
- Escalate to secondary if unable to resolve within **30 minutes**

#### Secondary On-Call
- Available as backup for primary on-call
- Respond when escalated by primary
- Take over if primary is unavailable

#### Escalation Manager
- Available for complex incidents requiring management decisions
- Coordinate with external teams and stakeholders
- Make decisions about service degradation vs. downtime

## 🚨 Alert Response Procedures

### Critical Alert: HighApiErrorRate

**Alert Trigger**: API 5xx error rate > 5% for 2+ minutes

#### Immediate Response (0-5 minutes)
1. **Acknowledge the alert** in PagerDuty
2. **Check Grafana Dashboard**: [API Error Rate Dashboard](https://grafana.company.com/d/gremlinsai/api-dashboard)
   - Look at error rate trends over last 1h, 6h, 24h
   - Identify which endpoints are failing
   - Check error distribution by status code

3. **Quick Health Check**:
   ```bash
   # Check service health
   kubectl get pods -n gremlinsai
   kubectl get services -n gremlinsai
   
   # Check recent deployments
   kubectl rollout history deployment/gremlinsai-backend-blue -n gremlinsai
   kubectl rollout history deployment/gremlinsai-backend-green -n gremlinsai
   ```

#### Investigation (5-15 minutes)
4. **Review Application Logs**:
   ```bash
   # Get recent error logs
   kubectl logs -n gremlinsai deployment/gremlinsai-backend-blue --tail=100 | grep ERROR
   
   # Check for specific error patterns
   kubectl logs -n gremlinsai deployment/gremlinsai-backend-blue --since=10m | grep -E "(500|502|503|504)"
   ```

5. **Check Downstream Dependencies**:
   - **Database**: Check PostgreSQL connection and performance
   - **Weaviate**: Verify vector database availability
   - **LLM Providers**: Check Ollama/external LLM status
   - **Redis**: Verify cache service health

6. **Review Recent Changes**:
   - Check if error rate correlates with recent deployments
   - Review recent configuration changes
   - Check for infrastructure changes

#### Mitigation (15-30 minutes)
7. **If Recent Deployment Caused Issue**:
   ```bash
   # Rollback to previous version
   kubectl patch service gremlinsai-service -n gremlinsai \
     -p '{"spec":{"selector":{"version":"blue"}}}'  # or green
   
   # Verify rollback
   ./scripts/deployment/validate-deployment.sh
   ```

8. **If Infrastructure Issue**:
   - Scale up replicas if resource constrained
   - Restart unhealthy pods
   - Check node health and resources

9. **If Dependency Issue**:
   - Restart dependent services
   - Enable circuit breakers if available
   - Implement graceful degradation

#### Escalation
- **Escalate to secondary** if unable to identify root cause within 15 minutes
- **Escalate to manager** if service downtime > 30 minutes
- **Escalate to VP** if customer-facing impact > 1 hour

### Critical Alert: HighLLMLatency

**Alert Trigger**: LLM P99 latency > 10 seconds for 3+ minutes

#### Immediate Response (0-5 minutes)
1. **Acknowledge the alert** in PagerDuty
2. **Check LLM Dashboard**: [LLM Performance Dashboard](https://grafana.company.com/d/gremlinsai/llm-dashboard)
   - Review latency trends by provider
   - Check request volume and success rates
   - Identify which LLM provider is affected

#### Investigation (5-15 minutes)
3. **Check LLM Provider Health**:
   ```bash
   # Check Ollama service status
   kubectl get pods -n gremlinsai -l app=ollama
   kubectl logs -n gremlinsai deployment/ollama --tail=50
   
   # Test LLM connectivity
   kubectl exec -n gremlinsai deployment/gremlinsai-backend-blue -- \
     curl -f http://ollama:11434/api/tags
   ```

4. **Review Connection Pool Metrics**:
   - Check connection pool efficiency in Grafana
   - Look for connection timeouts or pool exhaustion
   - Review concurrent request patterns

5. **Check Resource Utilization**:
   ```bash
   # Check CPU and memory usage
   kubectl top pods -n gremlinsai
   kubectl describe nodes
   ```

#### Mitigation (15-30 minutes)
6. **If Ollama Performance Issue**:
   - Restart Ollama service
   - Scale up Ollama replicas
   - Switch to fallback LLM provider

7. **If Connection Pool Issue**:
   - Increase pool size configuration
   - Restart application to reset connections

8. **If Resource Constraint**:
   - Scale up application replicas
   - Request additional cluster resources

### Critical Alert: WeaviateDown

**Alert Trigger**: Weaviate cluster unreachable for 1+ minute

#### Immediate Response (0-5 minutes)
1. **Acknowledge the alert** in PagerDuty
2. **Check Weaviate Status**:
   ```bash
   # Check Weaviate pods
   kubectl get pods -n gremlinsai -l app=weaviate
   kubectl describe pods -n gremlinsai -l app=weaviate
   ```

3. **Test Connectivity**:
   ```bash
   # Test from application pod
   kubectl exec -n gremlinsai deployment/gremlinsai-backend-blue -- \
     curl -f http://weaviate:8080/v1/meta
   ```

#### Investigation & Mitigation (5-20 minutes)
4. **If Pod Issues**:
   ```bash
   # Restart Weaviate pods
   kubectl rollout restart deployment/weaviate -n gremlinsai
   
   # Check for resource issues
   kubectl describe nodes
   kubectl get events -n gremlinsai --sort-by='.lastTimestamp'
   ```

5. **If Persistent Volume Issues**:
   ```bash
   # Check PV status
   kubectl get pv,pvc -n gremlinsai
   kubectl describe pvc weaviate-data -n gremlinsai
   ```

6. **If Network Issues**:
   - Check service and endpoint status
   - Verify network policies
   - Test DNS resolution

## 📊 Monitoring & Dashboards

### Primary Dashboards
1. **[GremlinsAI Overview](https://grafana.company.com/d/gremlinsai/overview)**
   - System health summary
   - Key performance indicators
   - Alert status overview

2. **[API Performance](https://grafana.company.com/d/gremlinsai/api-dashboard)**
   - Request rates and latency
   - Error rates by endpoint
   - Response time distributions

3. **[LLM Performance](https://grafana.company.com/d/gremlinsai/llm-dashboard)**
   - LLM response times by provider
   - Token usage and costs
   - Fallback rates and success metrics

4. **[Infrastructure Health](https://grafana.company.com/d/gremlinsai/infrastructure)**
   - Kubernetes cluster status
   - Node and pod health
   - Resource utilization

### Log Locations
- **Application Logs**: `kubectl logs -n gremlinsai deployment/gremlinsai-backend-{blue|green}`
- **Weaviate Logs**: `kubectl logs -n gremlinsai deployment/weaviate`
- **Ollama Logs**: `kubectl logs -n gremlinsai deployment/ollama`
- **Ingress Logs**: `kubectl logs -n ingress-nginx deployment/nginx-ingress-controller`

### Key Metrics to Monitor
- **API Error Rate**: Should be < 1%
- **API P95 Latency**: Should be < 2 seconds
- **LLM P99 Latency**: Should be < 10 seconds
- **Memory Usage**: Should be < 80% of limits
- **CPU Usage**: Should be < 70% of limits

## 🔄 Escalation Procedures

### Escalation Timeline
- **0-5 minutes**: Primary on-call responds and acknowledges
- **15 minutes**: Escalate to secondary if no progress
- **30 minutes**: Escalate to engineering manager
- **1 hour**: Escalate to VP Engineering for customer impact
- **2 hours**: Consider external communication and status page updates

### Escalation Criteria
- **Immediate Escalation**: Complete service outage
- **15-minute Escalation**: Unable to identify root cause
- **30-minute Escalation**: Mitigation attempts unsuccessful
- **1-hour Escalation**: Customer-facing impact continues

### Communication Channels
- **Internal**: #gremlinsai-alerts Slack channel
- **Engineering**: #engineering-incidents Slack channel
- **Leadership**: Direct phone calls for critical issues
- **External**: Status page updates for customer communication

## 📝 Post-Incident Procedures

### Immediate Post-Resolution (0-2 hours)
1. **Confirm Resolution**:
   - Verify all alerts have cleared
   - Check that metrics have returned to normal
   - Validate service functionality

2. **Initial Communication**:
   - Update incident channel with resolution
   - Notify stakeholders of service restoration
   - Update status page if customer-facing

3. **Preserve Evidence**:
   - Save relevant logs and metrics
   - Take screenshots of dashboards
   - Document timeline of events

### Post-Mortem Process (24-72 hours)
4. **Schedule Post-Mortem Meeting**:
   - Include all responders and stakeholders
   - Schedule within 24 hours of resolution
   - Book 1-2 hour meeting depending on complexity

5. **Prepare Post-Mortem Document**:
   ```markdown
   # Incident Post-Mortem: [Date] - [Brief Description]
   
   ## Summary
   - **Duration**: [Start time] - [End time]
   - **Impact**: [Customer impact description]
   - **Root Cause**: [Technical root cause]
   
   ## Timeline
   - [Time]: [Event description]
   
   ## Root Cause Analysis
   - [Detailed technical analysis]
   
   ## Action Items
   - [ ] [Action item with owner and due date]
   
   ## Lessons Learned
   - [What went well]
   - [What could be improved]
   ```

6. **Follow-Up Actions**:
   - Assign action items with owners and due dates
   - Schedule follow-up reviews
   - Update runbooks and procedures
   - Implement preventive measures

### Post-Mortem Template Location
- **Template**: [Confluence Post-Mortem Template](https://wiki.company.com/templates/post-mortem)
- **Storage**: All post-mortems stored in [Incident Database](https://wiki.company.com/incidents/)

## 🛠️ Tools & Resources

### Essential Tools
- **PagerDuty**: Alert management and escalation
- **Grafana**: Metrics visualization and dashboards
- **Prometheus**: Metrics collection and alerting
- **Slack**: Team communication and notifications
- **kubectl**: Kubernetes cluster management
- **Confluence**: Documentation and runbooks

### Quick Reference Commands
```bash
# Check overall system health
kubectl get pods -n gremlinsai
kubectl get services -n gremlinsai

# View recent logs
kubectl logs -n gremlinsai deployment/gremlinsai-backend-blue --tail=100

# Check resource usage
kubectl top pods -n gremlinsai
kubectl top nodes

# Restart deployment
kubectl rollout restart deployment/gremlinsai-backend-blue -n gremlinsai

# Scale deployment
kubectl scale deployment/gremlinsai-backend-blue --replicas=5 -n gremlinsai

# Check deployment status
kubectl rollout status deployment/gremlinsai-backend-blue -n gremlinsai
```

### Emergency Contacts
- **Cloud Provider Support**: [Provider-specific emergency contact]
- **Database Support**: [Database vendor support]
- **Network Operations**: [NOC contact information]

## 📚 Additional Resources

### Runbook Links
- [High API Error Rate Runbook](https://wiki.company.com/gremlinsai/runbooks/high-api-error-rate)
- [High LLM Latency Runbook](https://wiki.company.com/gremlinsai/runbooks/high-llm-latency)
- [Weaviate Down Runbook](https://wiki.company.com/gremlinsai/runbooks/weaviate-down)
- [Database Issues Runbook](https://wiki.company.com/gremlinsai/runbooks/database-issues)

### Architecture Documentation
- [GremlinsAI System Architecture](https://wiki.company.com/gremlinsai/architecture)
- [Deployment Architecture](https://wiki.company.com/gremlinsai/deployment)
- [Monitoring Setup](https://wiki.company.com/gremlinsai/monitoring)

### Training Materials
- [On-Call Training Guide](https://wiki.company.com/training/on-call)
- [Incident Response Training](https://wiki.company.com/training/incident-response)
- [GremlinsAI System Overview](https://wiki.company.com/gremlinsai/overview)

---

**Last Updated**: [Current Date]  
**Document Owner**: Platform Team  
**Review Schedule**: Monthly  
**Next Review**: [Next Month]
