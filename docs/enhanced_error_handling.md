# Enhanced Error Handling - gremlinsAI API

## Overview

The gremlinsAI API now features a comprehensive error handling system that provides structured, informative error responses with detailed context, remediation guidance, and service degradation indicators. This enhancement significantly improves the developer experience for both direct API consumers and SDK users.

## Key Features

### 🎯 **Standardized Error Responses**
- Consistent error format across all API endpoints
- Unique request IDs for tracking and debugging
- Detailed error categorization and severity levels
- Comprehensive error codes with clear naming conventions

### 🔧 **Enhanced Error Context**
- Processing step identification for multi-step operations
- Progress indicators for long-running tasks
- Service degradation status and fallback availability
- Field-level validation error details

### 🛡️ **Graceful Degradation**
- Service availability monitoring
- Fallback capability indicators
- Affected functionality identification
- Automatic service health tracking

### 📚 **Developer-Friendly Documentation**
- Interactive error examples in OpenAPI docs
- Suggested remediation actions
- Links to relevant documentation
- Clear error categorization

## Error Response Structure

### Standard Error Response Format

```json
{
  "success": false,
  "error_code": "GREMLINS_6001",
  "error_message": "Audio processing failed during transcription",
  "error_details": "Whisper model failed to process audio file: unsupported sample rate",
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "severity": "medium",
  "category": "multimodal_processing",
  "suggested_action": "Convert audio to supported format (WAV, MP3) with sample rate 16kHz or 44.1kHz",
  "documentation_url": "https://docs.gremlinsai.com/multimodal/audio-processing",
  "affected_services": [
    {
      "service_name": "audio_transcription",
      "status": "degraded",
      "fallback_available": true,
      "capabilities_affected": ["speech_to_text"]
    }
  ],
  "fallback_available": true,
  "validation_errors": [],
  "processing_step": "audio_transcription",
  "processing_progress": 0.3
}
```

### Error Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `false` for error responses |
| `error_code` | string | Standardized error code (e.g., `GREMLINS_6001`) |
| `error_message` | string | Human-readable error message |
| `error_details` | string | Additional context and technical details |
| `request_id` | string | Unique identifier for request tracking |
| `timestamp` | string | ISO timestamp of error occurrence |
| `severity` | string | Error severity: `low`, `medium`, `high`, `critical` |
| `category` | string | Error category for classification |
| `suggested_action` | string | Recommended action to resolve the error |
| `documentation_url` | string | Link to relevant documentation |
| `affected_services` | array | Services affected by this error |
| `fallback_available` | boolean | Whether fallback functionality exists |
| `validation_errors` | array | Detailed field-level validation errors |
| `processing_step` | string | Step where processing failed |
| `processing_progress` | number | Progress when error occurred (0.0-1.0) |

## Error Codes

### Error Code Categories

#### General Errors (1000-1999)
- `GREMLINS_1000` - Internal Server Error
- `GREMLINS_1001` - Invalid Request
- `GREMLINS_1002` - Resource Not Found
- `GREMLINS_1003` - Validation Error
- `GREMLINS_1004` - Rate Limit Exceeded

#### Authentication/Authorization (2000-2999)
- `GREMLINS_2000` - Authentication Required
- `GREMLINS_2001` - Invalid API Key
- `GREMLINS_2002` - Insufficient Permissions
- `GREMLINS_2003` - Token Expired

#### Agent Processing (3000-3999)
- `GREMLINS_3000` - Agent Processing Failed
- `GREMLINS_3001` - Agent Timeout
- `GREMLINS_3002` - Tool Execution Failed
- `GREMLINS_3003` - Context Too Large

#### Multi-Agent (4000-4999)
- `GREMLINS_4000` - Multi-Agent Orchestration Failed
- `GREMLINS_4001` - Agent Communication Error
- `GREMLINS_4002` - Workflow Execution Failed
- `GREMLINS_4003` - Agent Unavailable

#### Document Processing (5000-5999)
- `GREMLINS_5000` - Document Upload Failed
- `GREMLINS_5001` - Document Processing Failed
- `GREMLINS_5002` - Vector Store Error
- `GREMLINS_5003` - Search Failed
- `GREMLINS_5004` - Document Too Large

#### Multi-Modal Processing (6000-6999)
- `GREMLINS_6000` - Multi-Modal Processing Failed
- `GREMLINS_6001` - Audio Processing Failed
- `GREMLINS_6002` - Video Processing Failed
- `GREMLINS_6003` - Image Processing Failed
- `GREMLINS_6004` - Unsupported Media Format
- `GREMLINS_6005` - Media File Too Large
- `GREMLINS_6006` - Transcription Failed

#### Orchestrator (7000-7999)
- `GREMLINS_7000` - Task Execution Failed
- `GREMLINS_7001` - Task Timeout
- `GREMLINS_7002` - Worker Unavailable
- `GREMLINS_7003` - Task Queue Full

#### External Services (8000-8999)
- `GREMLINS_8000` - External Service Unavailable
- `GREMLINS_8001` - OpenAI API Error
- `GREMLINS_8002` - Qdrant Connection Error
- `GREMLINS_8003` - Redis Connection Error
- `GREMLINS_8004` - WebSocket Connection Error

#### Database (9000-9999)
- `GREMLINS_9000` - Database Connection Error
- `GREMLINS_9001` - Database Query Failed
- `GREMLINS_9002` - Conversation Not Found
- `GREMLINS_9003` - Data Integrity Error

## Service Degradation Handling

### Service Status Indicators

The API provides real-time information about service availability and degradation:

```json
{
  "service_name": "openai_api",
  "status": "degraded",
  "fallback_available": true,
  "capabilities_affected": ["gpt_analysis", "advanced_reasoning"]
}
```

### Service Status Values
- `available` - Service is fully operational
- `degraded` - Service has limited functionality, fallbacks available
- `unavailable` - Service is not accessible, no fallbacks

### Monitored Services
- **OpenAI API** - GPT analysis, advanced reasoning, multi-agent collaboration
- **Qdrant** - Semantic search, document similarity, RAG enhancement
- **Redis** - Task queuing, caching, session management
- **Whisper** - Speech-to-text, audio transcription
- **OpenCV** - Video processing, frame extraction
- **FFmpeg** - Video/audio format conversion

## Validation Error Details

### Field-Level Validation Errors

For validation failures, the API provides detailed field-level information:

```json
{
  "validation_errors": [
    {
      "field": "file",
      "message": "File must be an audio file",
      "invalid_value": "text/plain",
      "expected_type": "audio/*"
    },
    {
      "field": "transcribe",
      "message": "Must be a boolean value",
      "invalid_value": "yes",
      "expected_type": "boolean"
    }
  ]
}
```

### Validation Error Fields
- `field` - The field path that failed validation
- `message` - Human-readable validation error message
- `invalid_value` - The actual value that was provided
- `expected_type` - Expected data type or format

## Error Severity Levels

### Severity Classification

| Severity | Description | Impact | Action Required |
|----------|-------------|--------|-----------------|
| `low` | Minor issues, system continues normally | Minimal | Optional correction |
| `medium` | Some functionality affected, fallbacks available | Moderate | Recommended fix |
| `high` | Major functionality affected, limited fallbacks | Significant | Required attention |
| `critical` | System functionality severely impacted | Severe | Immediate action |

## Multi-Modal Error Context

### Processing Step Identification

For multi-modal operations, errors include specific processing step information:

```json
{
  "processing_step": "audio_transcription",
  "processing_progress": 0.3,
  "media_type": "audio",
  "fallback_available": true
}
```

### Common Processing Steps
- **Audio**: `file_validation`, `format_conversion`, `audio_transcription`, `audio_analysis`
- **Video**: `file_validation`, `frame_extraction`, `audio_extraction`, `video_analysis`
- **Image**: `file_validation`, `format_conversion`, `image_analysis`, `ocr_processing`

## SDK Integration

### Python SDK Error Handling

```python
from gremlins_ai import GremlinsAIClient
from gremlins_ai.exceptions import (
    ValidationError, 
    ProcessingError, 
    ServiceUnavailableError
)

client = GremlinsAIClient()

try:
    result = await client.process_audio(file_path="audio.wav")
except ValidationError as e:
    print(f"Validation failed: {e.error_message}")
    for error in e.validation_errors:
        print(f"  {error.field}: {error.message}")
except ProcessingError as e:
    print(f"Processing failed at step: {e.processing_step}")
    if e.fallback_available:
        print("Fallback options are available")
except ServiceUnavailableError as e:
    print(f"Service unavailable: {e.service_name}")
    print(f"Affected capabilities: {e.capabilities_affected}")
```

### JavaScript/TypeScript Integration

```typescript
import { GremlinsAIClient, ErrorCode } from '@gremlins-ai/client';

const client = new GremlinsAIClient();

try {
  const result = await client.processAudio({ file: audioFile });
} catch (error) {
  if (error.errorCode === ErrorCode.AUDIO_PROCESSING_FAILED) {
    console.log(`Audio processing failed: ${error.errorMessage}`);
    console.log(`Processing step: ${error.processingStep}`);
    
    if (error.fallbackAvailable) {
      console.log('Fallback processing available');
    }
  }
}
```

## Best Practices

### For API Consumers

1. **Always Check Error Codes**: Use standardized error codes for programmatic error handling
2. **Implement Retry Logic**: For temporary failures with appropriate backoff strategies
3. **Handle Service Degradation**: Check `fallback_available` and adapt functionality accordingly
4. **Log Request IDs**: Include request IDs in your logs for easier debugging
5. **Monitor Service Health**: Use service status information to adapt application behavior

### For SDK Developers

1. **Map Error Codes**: Create language-specific exception classes for different error types
2. **Preserve Context**: Include all error context (processing step, progress, etc.) in exceptions
3. **Implement Fallbacks**: Provide automatic fallback mechanisms when services are degraded
4. **Provide Utilities**: Create helper functions for common error handling patterns

## Monitoring and Debugging

### Request Tracking

Every error response includes a unique `request_id` that can be used for:
- Correlating errors across distributed systems
- Debugging specific user issues
- Performance monitoring and analysis

### Service Health Monitoring

The API provides endpoints for monitoring overall system health:

```bash
GET /api/v1/health
GET /api/v1/health/services
GET /developer-portal  # Real-time dashboard
```

### Error Analytics

Error responses include structured data that enables:
- Error rate monitoring by category and severity
- Service degradation impact analysis
- Processing step failure analysis
- User experience impact assessment

## Migration Guide

### Updating Existing Code

If you're upgrading from the previous error handling system:

1. **Update Error Parsing**: Expect the new structured error format
2. **Handle New Fields**: Process `error_code`, `severity`, and `affected_services`
3. **Implement Fallback Logic**: Use `fallback_available` to provide alternative functionality
4. **Update Logging**: Include `request_id` and error context in logs

### Backward Compatibility

The enhanced error handling system maintains backward compatibility:
- HTTP status codes remain unchanged
- Basic error messages are still provided
- Existing error handling code will continue to work
- New fields are additive and optional to process

---

The enhanced error handling system provides a robust foundation for building reliable applications with the gremlinsAI API, offering clear error communication, graceful degradation, and comprehensive debugging capabilities.
