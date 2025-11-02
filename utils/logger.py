import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from strand_agents import Agent, AgentConfig
from models.alert import Alert
from models.classification import Classification
from config import Config


class LoggingAgent(Agent):
    """Strand Agent for structured logging and audit trails."""
    
    def __init__(self):
        config = AgentConfig(
            name="logging_agent",
            description="Manages structured logging and audit trails"
        )
        super().__init__(config)
        self.log_file_path = Config.LOG_FILE
        self.session_stats = {
            "start_time": datetime.now(),
            "alerts_processed": 0,
            "actions_taken": {},
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize logging system."""
        # Setup Python logging
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.log_info("Logging agent initialized")
    
    async def log_decision(
        self, 
        alert: Alert, 
        classification: Classification, 
        action_taken: str, 
        execution_status: str,
        processing_time_ms: int,
        error_message: Optional[str] = None
    ):
        """Log a triage decision to the audit file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "alert_id": alert.id,
                "device_name": alert.device_name,
                "alert_type": alert.alert_type,
                "ai_classification": classification.to_dict(),
                "action_taken": action_taken,
                "execution_status": execution_status,
                "processing_time_ms": processing_time_ms
            }
            
            if error_message:
                log_entry["error_message"] = error_message
            
            # Append to log file
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Update session stats
            self.session_stats["alerts_processed"] += 1
            action = classification.action
            self.session_stats["actions_taken"][action] = self.session_stats["actions_taken"].get(action, 0) + 1
            
            if execution_status == "error":
                self.session_stats["errors"] += 1
            
            self.log_info(f"Logged decision for alert {alert.id}: {action_taken}")
            
        except Exception as e:
            self.log_error(f"Failed to log decision: {e}")
    
    async def log_summary(self):
        """Log session summary with time savings calculation."""
        try:
            end_time = datetime.now()
            session_duration = (end_time - self.session_stats["start_time"]).total_seconds()
            
            # Calculate time savings (3 min manual vs 5 sec automated per alert)
            manual_time_per_alert = 180  # 3 minutes in seconds
            automated_time_per_alert = 5  # 5 seconds
            time_saved_per_alert = manual_time_per_alert - automated_time_per_alert
            total_time_saved = self.session_stats["alerts_processed"] * time_saved_per_alert
            
            summary = {
                "timestamp": end_time.isoformat(),
                "session_type": "summary",
                "session_duration_seconds": round(session_duration, 2),
                "total_alerts_processed": self.session_stats["alerts_processed"],
                "actions_breakdown": self.session_stats["actions_taken"],
                "errors_encountered": self.session_stats["errors"],
                "time_savings": {
                    "per_alert_seconds": time_saved_per_alert,
                    "total_saved_seconds": total_time_saved,
                    "total_saved_minutes": round(total_time_saved / 60, 1),
                    "daily_projection_minutes": round((total_time_saved / 60) * (self.session_stats["alerts_processed"] / 10) * 10, 1) if self.session_stats["alerts_processed"] > 0 else 0
                }
            }
            
            # Append summary to log file
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(summary) + '\n')
            
            self.log_info(f"Session summary logged: {self.session_stats['alerts_processed']} alerts processed, {round(total_time_saved/60, 1)} minutes saved")
            
            return summary
            
        except Exception as e:
            self.log_error(f"Failed to log summary: {e}")
            return None
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return self.session_stats.copy()