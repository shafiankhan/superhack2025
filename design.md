# Design Document

## Overview

NinjaTriage AI is a Python-based automation agent that integrates with NinjaRMM to provide intelligent alert triage capabilities. The system uses Playwright for web automation, AWS Bedrock for AI-powered decision making, and AWS Secrets Manager for secure credential storage. The architecture follows a modular design pattern with clear separation of concerns for authentication, scraping, AI analysis, action execution, and logging.

## Architecture

The system operates as a single-threaded, sequential processor that handles alerts one at a time to ensure reliable operation and clear audit trails.

**Core Components:**
- Main Controller: Orchestrates the entire workflow
- Credential Manager: Handles AWS Secrets Manager integration
- NinjaRMM Scraper: Automates browser interaction with Playwright
- AI Classifier: Integrates with AWS Bedrock GPT-4o
- Action Executor: Performs classified actions
- Logger: Manages structured logging and audit trails

## Components and Interfaces

### 1. Main Controller (`ninja_triage.py`)
**Purpose:** Orchestrates the entire triage workflow
**Key Methods:**
- `run()`: Main execution loop
- `process_alerts()`: Coordinates alert processing pipeline
- `generate_summary()`: Creates session summary with time savings

### 2. Credential Manager (`auth/credential_manager.py`)
**Purpose:** Handles secure credential retrieval and management
**Key Methods:**
- `get_ninja_credentials()`: Retrieves NinjaRMM login credentials from AWS Secrets Manager
- `clear_credentials()`: Securely clears credentials from memory
**Dependencies:** boto3 for AWS Secrets Manager integration

### 3. NinjaRMM Scraper (`scraping/ninja_scraper.py`)
**Purpose:** Automates browser interaction with NinjaRMM
**Key Methods:**
- `login(username, password)`: Authenticates with NinjaRMM
- `scrape_alerts(limit=10)`: Extracts alert data from dashboard
- `close()`: Properly closes browser session
**Dependencies:** Playwright for browser automation

### 4. AI Classifier (`ai/alert_classifier.py`)
**Purpose:** Analyzes alerts using GPT-4o and determines appropriate actions
**Key Methods:**
- `classify_alert(alert_text)`: Sends alert to GPT-4o for analysis
- `parse_ai_response(response)`: Validates and parses JSON response
**Dependencies:** boto3 for AWS Bedrock integration

### 5. Action Executor (`actions/executor.py`)
**Purpose:** Executes actions based on AI classification
**Key Methods:**
- `execute_reboot(device_info)`: Simulates reboot command
- `notify_client(alert_info)`: Handles client notification
- `create_ticket(alert_data)`: Posts to SuperOps webhook
- `ignore_alert(reason)`: Logs ignored alerts
**Dependencies:** requests for HTTP calls

### 6. Logger (`utils/logger.py`)
**Purpose:** Manages structured logging and audit trails
**Key Methods:**
- `log_decision(alert, classification, action, status)`: Records triage decisions
- `log_summary(total_alerts, time_saved)`: Creates session summary
- `setup_logging()`: Configures logging infrastructure
## D
ata Models

### Alert Data Structure
```python
@dataclass
class Alert:
    id: str
    device_name: str
    alert_type: str
    description: str
    severity: str
    timestamp: datetime
    raw_text: str
```

### AI Classification Response
```python
@dataclass
class Classification:
    action: str  # "reboot" | "notify_client" | "create_ticket" | "ignore"
    reason: str
    confidence: str  # "High" | "Medium" | "Low"
```

### Log Entry Structure
```json
{
    "timestamp": "2025-01-15T10:30:00Z",
    "alert_id": "ALT-12345",
    "device_name": "SERVER-01",
    "alert_type": "Pending Reboot",
    "ai_classification": {
        "action": "reboot",
        "reason": "System requires restart after Windows updates",
        "confidence": "High"
    },
    "action_taken": "reboot_simulated",
    "execution_status": "success",
    "processing_time_ms": 1250
}
```

## Error Handling

### Authentication Errors
- **Credential Retrieval Failure:** Log error, exit gracefully with code 1
- **Login Failure:** Retry up to 3 times with exponential backoff, then exit
- **Session Timeout:** Attempt re-authentication once, then fail gracefully

### Scraping Errors
- **Page Load Timeout:** Retry once, skip alert if persistent
- **Element Not Found:** Log warning, continue with available alerts
- **Network Issues:** Implement retry logic with circuit breaker pattern

### AI Classification Errors
- **Invalid JSON Response:** Log error, classify as "ignore"
- **API Rate Limiting:** Implement exponential backoff
- **Service Unavailable:** Retry with fallback to manual classification rules

### Action Execution Errors
- **Webhook Failures:** Log error, continue processing
- **Network Timeouts:** Retry once, then log failure
- **Invalid Responses:** Log detailed error information

## Testing Strategy

### Unit Tests
- **Credential Manager:** Mock AWS Secrets Manager responses
- **AI Classifier:** Mock Bedrock API calls with various response scenarios
- **Action Executor:** Mock HTTP requests and validate payloads
- **Logger:** Verify JSON structure and file operations

### Integration Tests
- **End-to-End Workflow:** Use test NinjaRMM environment with known alerts
- **AWS Integration:** Test with actual AWS services in development environment
- **Error Scenarios:** Simulate various failure conditions

### Performance Tests
- **Alert Processing Speed:** Measure time per alert (target: <5 seconds)
- **Memory Usage:** Monitor for memory leaks during extended runs
- **Concurrent Load:** Test system behavior under high alert volumes

### Security Tests
- **Credential Handling:** Verify no credentials appear in logs or memory dumps
- **Input Validation:** Test with malformed alert data
- **Network Security:** Validate HTTPS usage and certificate verification