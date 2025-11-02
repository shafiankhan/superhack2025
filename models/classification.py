from dataclasses import dataclass
from typing import Literal


@dataclass
class Classification:
    """AI classification response structure."""
    
    action: Literal["reboot", "notify_client", "create_ticket", "ignore"]
    reason: str
    confidence: Literal["High", "Medium", "Low"]
    
    def __post_init__(self):
        """Validate classification data."""
        valid_actions = ["reboot", "notify_client", "create_ticket", "ignore"]
        if self.action not in valid_actions:
            raise ValueError(f"Invalid action: {self.action}. Must be one of {valid_actions}")
        
        valid_confidence = ["High", "Medium", "Low"]
        if self.confidence not in valid_confidence:
            raise ValueError(f"Invalid confidence: {self.confidence}. Must be one of {valid_confidence}")
    
    def to_dict(self) -> dict:
        """Convert classification to dictionary."""
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Classification":
        """Create Classification from dictionary."""
        return cls(
            action=data["action"],
            reason=data["reason"],
            confidence=data["confidence"]
        )