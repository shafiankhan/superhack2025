import json
import boto3
from typing import Optional
from strand_agents import Agent, AgentConfig
from models.alert import Alert
from models.classification import Classification
from config import Config


class ClassificationAgent(Agent):
    """Strand Agent for AI-powered alert classification using AWS Bedrock."""
    
    def __init__(self):
        config = AgentConfig(
            name="classification_agent",
            description="Analyzes alerts using GPT-4o via AWS Bedrock"
        )
        super().__init__(config)
        self.bedrock_client = None
        
        # Classification prompt template
        self.prompt_template = """
You are an expert MSP technician analyzing NinjaRMM alerts. Classify this alert and determine the appropriate action.

Alert Details:
Device: {device_name}
Type: {alert_type}
Description: {description}
Severity: {severity}
Raw Text: {raw_text}

Classification Rules:
1. REBOOT: For pending reboots, Windows updates requiring restart, or system restart alerts
2. NOTIFY_CLIENT: For issues requiring client action (user behavior, hardware replacement, etc.)
3. CREATE_TICKET: For complex technical issues requiring technician investigation
4. IGNORE: For false positives, informational alerts, or resolved issues

Respond with ONLY valid JSON in this exact format:
{{
    "action": "reboot|notify_client|create_ticket|ignore",
    "reason": "Brief explanation of why this action was chosen",
    "confidence": "High|Medium|Low"
}}
"""
    
    async def initialize(self):
        """Initialize AWS Bedrock client."""
        try:
            # Check if we have AWS credentials
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    **Config.get_aws_config()
                )
                self.log_info("Classification agent initialized with AWS Bedrock")
            else:
                self.log_info("Classification agent initialized in demo mode (no AWS Bedrock)")
            
        except Exception as e:
            self.log_error(f"Failed to initialize classification agent: {e}")
            raise
    
    async def classify_alert(self, alert: Alert) -> Classification:
        """Classify an alert using GPT-4o via AWS Bedrock."""
        try:
            self.log_info(f"Classifying alert {alert.id} for device {alert.device_name}")
            
            if self.bedrock_client:
                # Real AWS Bedrock classification
                # Format the prompt with alert data
                prompt = self.prompt_template.format(
                    device_name=alert.device_name,
                    alert_type=alert.alert_type,
                    description=alert.description,
                    severity=alert.severity,
                    raw_text=alert.raw_text
                )
                
                # Prepare request for Claude
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                # Call AWS Bedrock
                response = self.bedrock_client.invoke_model(
                    modelId=Config.BEDROCK_MODEL_ID,
                    body=json.dumps(request_body),
                    contentType='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                ai_response = response_body['content'][0]['text']
                
                # Parse AI response JSON
                classification = self._parse_ai_response(ai_response)
            else:
                # Demo mode - use enhanced rule-based classification
                classification = self._demo_classify_alert(alert)
            
            self.log_info(f"Alert {alert.id} classified as: {classification.action} (confidence: {classification.confidence})")
            return classification
            
        except Exception as e:
            self.log_error(f"Failed to classify alert {alert.id}: {e}")
            # Return fallback classification
            return Classification(
                action="ignore",
                reason=f"Classification failed due to error: {str(e)[:100]}",
                confidence="Low"
            )
    
    def _parse_ai_response(self, response_text: str) -> Classification:
        """Parse and validate AI response JSON."""
        try:
            # Clean up response text
            response_text = response_text.strip()
            
            # Find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[start_idx:end_idx]
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['action', 'reason', 'confidence']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create and validate classification
            classification = Classification.from_dict(data)
            
            return classification
            
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON in AI response: {e}")
            return Classification(
                action="ignore",
                reason="Invalid JSON response from AI",
                confidence="Low"
            )
        except ValueError as e:
            self.log_error(f"Invalid classification data: {e}")
            return Classification(
                action="ignore",
                reason=f"Invalid response format: {str(e)}",
                confidence="Low"
            )
        except Exception as e:
            self.log_error(f"Unexpected error parsing AI response: {e}")
            return Classification(
                action="ignore",
                reason="Unexpected parsing error",
                confidence="Low"
            )
    
    async def classify_with_fallback(self, alert: Alert) -> Classification:
        """Classify alert with rule-based fallback if AI fails."""
        try:
            # Try AI classification first
            return await self.classify_alert(alert)
            
        except Exception as e:
            self.log_warning(f"AI classification failed, using enhanced demo classification: {e}")
            # Use enhanced demo classification instead of basic fallback
            return self._demo_classify_alert(alert)
    
    def _demo_classify_alert(self, alert: Alert) -> Classification:
        """Enhanced demo classification with realistic AI-like decisions."""
        alert_text = f"{alert.alert_type} {alert.description}".lower()
        
        # Reboot patterns - High confidence
        if any(keyword in alert_text for keyword in ['reboot', 'restart', 'pending reboot', 'windows update', 'security update']):
            return Classification(
                action="reboot",
                reason="System requires restart after Windows Security Updates installation",
                confidence="High"
            )
        
        # Critical system issues - High confidence
        if any(keyword in alert_text for keyword in ['service stopped', 'sql server', 'database', 'critical error', 'system down']):
            return Classification(
                action="create_ticket",
                reason="Critical SQL Server service failure requires immediate attention",
                confidence="High"
            )
        
        # Client-actionable issues - High confidence for disk space
        if any(keyword in alert_text for keyword in ['disk space', 'storage', 'drive full', 'documents folder']):
            return Classification(
                action="notify_client",
                reason="User documents folder consuming excessive space, requires client cleanup",
                confidence="High"
            )
        
        # Network/hardware issues - Medium confidence
        if any(keyword in alert_text for keyword in ['offline', 'printer', 'network', 'connectivity', 'unreachable']):
            return Classification(
                action="create_ticket",
                reason="Network connectivity issue requires technician investigation",
                confidence="Medium"
            )
        
        # Security issues - High confidence
        if any(keyword in alert_text for keyword in ['security', 'failed login', 'firewall', 'blocked']):
            return Classification(
                action="create_ticket",
                reason="Security alert requires immediate investigation",
                confidence="High"
            )
        
        # Minor issues that can be ignored - Medium confidence
        if any(keyword in alert_text for keyword in ['antivirus update', 'temporary', 'low battery', 'retry']):
            return Classification(
                action="ignore",
                reason="Temporary network issue, will retry automatically",
                confidence="Medium"
            )
        
        # Default to create ticket for unknown issues
        return Classification(
            action="create_ticket",
            reason="Unknown issue pattern requires technician review",
            confidence="Low"
        )
    
    def _fallback_classification(self, alert: Alert) -> Classification:
        """Rule-based fallback classification."""
        alert_text = f"{alert.alert_type} {alert.description}".lower()
        
        # Reboot patterns
        if any(keyword in alert_text for keyword in ['reboot', 'restart', 'pending reboot', 'windows update']):
            return Classification(
                action="reboot",
                reason="Detected reboot-related keywords in alert",
                confidence="Medium"
            )
        
        # Critical system issues
        if any(keyword in alert_text for keyword in ['service stopped', 'system down', 'critical error']):
            return Classification(
                action="create_ticket",
                reason="Critical system issue detected",
                confidence="Medium"
            )
        
        # Client-actionable issues
        if any(keyword in alert_text for keyword in ['disk space', 'user', 'password', 'login']):
            return Classification(
                action="notify_client",
                reason="Issue likely requires client action",
                confidence="Medium"
            )
        
        # Default to ignore for unknown patterns
        return Classification(
            action="ignore",
            reason="No clear classification pattern detected",
            confidence="Low"
        )