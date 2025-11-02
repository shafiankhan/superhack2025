import asyncio
import json
from typing import Dict, Any, Tuple
import requests
from strand_agents import Agent, AgentConfig
from models.alert import Alert
from models.classification import Classification
from config import Config


class ActionAgent(Agent):
    """Strand Agent for executing classified actions."""
    
    def __init__(self):
        config = AgentConfig(
            name="action_agent",
            description="Executes actions based on AI classification"
        )
        super().__init__(config)
        self.session = None
    
    async def initialize(self):
        """Initialize HTTP session for webhook calls."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NinjaTriage-AI/1.0',
            'Content-Type': 'application/json'
        })
        self.log_info("Action agent initialized")
    
    async def execute_action(self, alert: Alert, classification: Classification) -> Tuple[str, str]:
        """Execute the classified action and return (action_taken, status)."""
        try:
            action = classification.action
            
            self.log_info(f"Executing action '{action}' for alert {alert.id}")
            
            if action == "reboot":
                return await self._execute_reboot(alert)
            elif action == "notify_client":
                return await self._notify_client(alert, classification)
            elif action == "create_ticket":
                return await self._create_ticket(alert, classification)
            elif action == "ignore":
                return await self._ignore_alert(alert, classification)
            else:
                self.log_error(f"Unknown action: {action}")
                return "unknown_action", "error"
                
        except Exception as e:
            self.log_error(f"Failed to execute action for alert {alert.id}: {e}")
            return f"execution_failed", "error"
    
    async def _execute_reboot(self, alert: Alert) -> Tuple[str, str]:
        """Simulate device reboot command."""
        try:
            self.log_info(f"Simulating reboot for device: {alert.device_name}")
            
            # Simulate reboot delay
            await asyncio.sleep(1)
            
            # In a real implementation, this would send actual reboot commands
            # via NinjaRMM API or other management tools
            
            print(f"🔄 REBOOT EXECUTED: {alert.device_name}")
            print(f"   Reason: {alert.description}")
            print(f"   Command: Restart-Computer -ComputerName {alert.device_name} -Force")
            
            self.log_info(f"Reboot command simulated for {alert.device_name}")
            return "reboot_simulated", "success"
            
        except Exception as e:
            self.log_error(f"Failed to execute reboot for {alert.device_name}: {e}")
            return "reboot_failed", "error"
    
    async def _notify_client(self, alert: Alert, classification: Classification) -> Tuple[str, str]:
        """Send notification to client."""
        try:
            self.log_info(f"Sending client notification for device: {alert.device_name}")
            
            # Simulate email sending delay
            await asyncio.sleep(0.5)
            
            # In a real implementation, this would integrate with email service
            # or client notification system
            
            print(f"📧 EMAIL SENT TO CLIENT")
            print(f"   Device: {alert.device_name}")
            print(f"   Issue: {alert.alert_type}")
            print(f"   Action Required: {classification.reason}")
            print(f"   To: client-{alert.device_name.lower()}@company.com")
            
            self.log_info(f"Client notification sent for {alert.device_name}")
            return "client_notified", "success"
            
        except Exception as e:
            self.log_error(f"Failed to notify client for {alert.device_name}: {e}")
            return "notification_failed", "error"
    
    async def _create_ticket(self, alert: Alert, classification: Classification) -> Tuple[str, str]:
        """Create ticket via SuperOps webhook."""
        try:
            self.log_info(f"Creating ticket for alert: {alert.id}")
            
            # Prepare ticket payload
            ticket_payload = {
                "title": f"{alert.alert_type} - {alert.device_name}",
                "description": alert.description,
                "priority": self._map_severity_to_priority(alert.severity),
                "device": alert.device_name,
                "alert_id": alert.id,
                "classification_reason": classification.reason,
                "confidence": classification.confidence,
                "timestamp": alert.timestamp.isoformat(),
                "source": "NinjaTriage-AI"
            }
            
            # Send to SuperOps webhook
            response = self.session.post(
                Config.SUPEROPS_WEBHOOK_URL,
                json=ticket_payload,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                print(f"🎫 TICKET CREATED")
                print(f"   Title: {ticket_payload['title']}")
                print(f"   Priority: {ticket_payload['priority']}")
                print(f"   Webhook Response: {response.status_code}")
                
                self.log_info(f"Ticket created successfully for alert {alert.id}")
                return "ticket_created", "success"
            else:
                self.log_error(f"Webhook returned status {response.status_code}: {response.text}")
                return "ticket_failed", "error"
                
        except requests.exceptions.RequestException as e:
            self.log_error(f"Network error creating ticket: {e}")
            # Still log as attempted for audit trail
            print(f"🎫 TICKET CREATION ATTEMPTED (Network Error)")
            print(f"   Device: {alert.device_name}")
            print(f"   Error: {str(e)[:100]}")
            return "ticket_network_error", "error"
            
        except Exception as e:
            self.log_error(f"Failed to create ticket for alert {alert.id}: {e}")
            return "ticket_failed", "error"
    
    async def _ignore_alert(self, alert: Alert, classification: Classification) -> Tuple[str, str]:
        """Log ignored alert."""
        try:
            print(f"⏭️  ALERT IGNORED")
            print(f"   Device: {alert.device_name}")
            print(f"   Type: {alert.alert_type}")
            print(f"   Reason: {classification.reason}")
            
            self.log_info(f"Alert {alert.id} ignored: {classification.reason}")
            return "alert_ignored", "success"
            
        except Exception as e:
            self.log_error(f"Failed to ignore alert {alert.id}: {e}")
            return "ignore_failed", "error"
    
    def _map_severity_to_priority(self, severity: str) -> str:
        """Map alert severity to ticket priority."""
        severity_map = {
            "Critical": "High",
            "High": "High", 
            "Medium": "Medium",
            "Low": "Low",
            "Info": "Low"
        }
        return severity_map.get(severity, "Medium")
    
    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session:
            self.session.close()
        self.log_info("Action agent cleanup completed")