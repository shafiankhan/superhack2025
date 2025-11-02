from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Alert:
    """Alert data structure for NinjaRMM alerts."""
    
    id: str
    device_name: str
    alert_type: str
    description: str
    severity: str
    timestamp: datetime
    raw_text: str
    
    def __post_init__(self):
        """Validate alert data after initialization."""
        if not self.id or not self.device_name:
            raise ValueError("Alert ID and device name are required")
        
        if self.severity not in ["Critical", "High", "Medium", "Low", "Info"]:
            self.severity = "Medium"  # Default fallback
    
    def to_dict(self) -> dict:
        """Convert alert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "device_name": self.device_name,
            "alert_type": self.alert_type,
            "description": self.description,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "raw_text": self.raw_text
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """Create Alert from dictionary."""
        # Handle timestamp conversion
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            if timestamp.endswith('Z'):
                timestamp = timestamp[:-1] + '+00:00'
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            id=data["id"],
            device_name=data["device_name"],
            alert_type=data["alert_type"],
            description=data["description"],
            severity=data["severity"],
            timestamp=timestamp,
            raw_text=data["raw_text"]
        )