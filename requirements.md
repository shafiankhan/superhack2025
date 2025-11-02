# Requirements Document

## Introduction

NinjaTriage AI is an automated alert triage system designed for Managed Service Providers (MSPs) using NinjaRMM. The system eliminates the manual overhead of checking and triaging alerts by automatically logging into NinjaRMM, analyzing alerts using AI, and taking appropriate actions based on alert classification. This solution addresses the significant time waste (2-4 hours/day per technician) currently spent on manual alert review and aims to auto-resolve 45% of common alerts with 92% accuracy.

## Requirements

### Requirement 1

**User Story:** As an MSP technician, I want the system to automatically log into NinjaRMM using secure credentials, so that I don't have to manually access the platform to check alerts.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL retrieve NinjaRMM credentials from AWS Secrets Manager
2. WHEN credentials are retrieved THEN the system SHALL use Playwright to automate browser login to NinjaRMM
3. IF login fails THEN the system SHALL log the error and retry up to 3 times
4. WHEN login is successful THEN the system SHALL navigate to the alerts dashboard

### Requirement 2

**User Story:** As an MSP technician, I want the system to automatically scrape and analyze the top 10 alerts from NinjaRMM, so that the most critical issues are prioritized for triage.

#### Acceptance Criteria

1. WHEN logged into NinjaRMM THEN the system SHALL scrape the top 10 alerts from the dashboard
2. WHEN alerts are scraped THEN the system SHALL extract full alert text including device name, alert type, and description
3. IF fewer than 10 alerts exist THEN the system SHALL process all available alerts
4. WHEN alert extraction is complete THEN the system SHALL prepare each alert for AI analysis

### Requirement 3

**User Story:** As an MSP technician, I want each alert to be analyzed by GPT-4o via AWS Bedrock with specific classification criteria, so that appropriate actions can be determined automatically.

#### Acceptance Criteria

1. WHEN an alert is ready for analysis THEN the system SHALL send it to GPT-4o via AWS Bedrock with the specified prompt template
2. WHEN GPT-4o responds THEN the system SHALL parse the JSON response containing action, reason, and confidence
3. IF the response is not valid JSON THEN the system SHALL log the error and classify as "ignore"
4. WHEN classification is complete THEN the system SHALL validate the action is one of: reboot, notify_client, create_ticket, or ignore

### Requirement 4

**User Story:** As an MSP technician, I want the system to automatically execute appropriate actions based on alert classification, so that common issues are resolved without manual intervention.

#### Acceptance Criteria

1. WHEN action is "reboot" THEN the system SHALL simulate a reboot command and log the action
2. WHEN action is "notify_client" THEN the system SHALL print "Email sent to client..." and log the notification
3. WHEN action is "create_ticket" THEN the system SHALL POST a mock payload to https://hooks.example.com/superops-ticket
4. WHEN action is "ignore" THEN the system SHALL skip processing and log the decision
5. IF action execution fails THEN the system SHALL log the error and continue with next alert

### Requirement 5

**User Story:** As an MSP manager, I want all agent decisions and actions to be logged in a structured format, so that I can audit the system's performance and track time savings.

#### Acceptance Criteria

1. WHEN any action is taken THEN the system SHALL log the decision to agent_log.json
2. WHEN logging THEN the system SHALL include timestamp, alert details, AI classification, action taken, and execution status
3. WHEN the session completes THEN the system SHALL append a summary with total alerts processed and estimated time saved
4. IF logging fails THEN the system SHALL continue operation but print error to console

### Requirement 6

**User Story:** As an MSP technician, I want the system to run headless in terminal mode with proper error handling, so that it can be deployed in automated environments without manual intervention.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL run in headless mode without GUI dependencies
2. WHEN errors occur THEN the system SHALL log detailed error messages and continue processing remaining alerts
3. IF critical errors occur THEN the system SHALL gracefully exit with appropriate error codes
4. WHEN processing completes THEN the system SHALL display a summary of actions taken and time saved

### Requirement 7

**User Story:** As a system administrator, I want secure credential management through AWS Secrets Manager, so that sensitive login information is never hardcoded or exposed.

#### Acceptance Criteria

1. WHEN the system needs credentials THEN it SHALL retrieve them from AWS Secrets Manager using proper IAM permissions
2. WHEN credentials are used THEN they SHALL never be logged or printed to console
3. IF credential retrieval fails THEN the system SHALL exit with an appropriate error message
4. WHEN credentials are no longer needed THEN they SHALL be cleared from memory

### Requirement 8

**User Story:** As a developer, I want clean, maintainable code with comprehensive documentation, so that the system can be easily deployed and maintained by other team members.

#### Acceptance Criteria

1. WHEN code is written THEN it SHALL follow Python best practices with proper error handling
2. WHEN the project is delivered THEN it SHALL include a comprehensive README.md with setup instructions
3. WHEN dependencies are used THEN they SHALL be clearly documented in requirements.txt
4. WHEN the system is deployed THEN it SHALL include sample configuration files and usage examples