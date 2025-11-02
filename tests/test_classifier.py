import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from models.alert import Alert
from models.classification import Classification
from ai.alert_classifier import ClassificationAgent


@pytest.fixture
def sample_alert():
    """Create a sample alert for testing."""
    return Alert(
        id="ALT-TEST-001",
        device_name="TEST-SERVER-01",
        alert_type="Pending Reboot",
        description="System requires restart after Windows updates",
        severity="High",
        timestamp=datetime.now(),
        raw_text="TEST-SERVER-01: Pending Reboot - System requires restart after Windows updates"
    )


@pytest.fixture
def classification_agent():
    """Create a classification agent for testing."""
    return ClassificationAgent()


class TestClassificationAgent:
    """Test cases for ClassificationAgent."""
    
    @pytest.mark.asyncio
    async def test_parse_valid_ai_response(self, classification_agent):
        """Test parsing valid AI response JSON."""
        response_text = '''
        {
            "action": "reboot",
            "reason": "System requires restart after updates",
            "confidence": "High"
        }
        '''
        
        classification = classification_agent._parse_ai_response(response_text)
        
        assert classification.action == "reboot"
        assert classification.reason == "System requires restart after updates"
        assert classification.confidence == "High"
    
    def test_parse_invalid_json_response(self, classification_agent):
        """Test parsing invalid JSON response."""
        response_text = "This is not valid JSON"
        
        classification = classification_agent._parse_ai_response(response_text)
        
        assert classification.action == "ignore"
        assert "Invalid JSON response" in classification.reason
        assert classification.confidence == "Low"
    
    def test_parse_missing_fields_response(self, classification_agent):
        """Test parsing response with missing required fields."""
        response_text = '{"action": "reboot"}'  # Missing reason and confidence
        
        classification = classification_agent._parse_ai_response(response_text)
        
        assert classification.action == "ignore"
        assert "Missing required field" in classification.reason
        assert classification.confidence == "Low"
    
    def test_fallback_classification_reboot(self, classification_agent, sample_alert):
        """Test fallback classification for reboot alerts."""
        sample_alert.alert_type = "Pending Reboot"
        sample_alert.description = "System needs restart after Windows update"
        
        classification = classification_agent._fallback_classification(sample_alert)
        
        assert classification.action == "reboot"
        assert "reboot-related keywords" in classification.reason
        assert classification.confidence == "Medium"
    
    def test_fallback_classification_critical(self, classification_agent, sample_alert):
        """Test fallback classification for critical issues."""
        sample_alert.alert_type = "Service Stopped"
        sample_alert.description = "SQL Server service has stopped unexpectedly"
        
        classification = classification_agent._fallback_classification(sample_alert)
        
        assert classification.action == "create_ticket"
        assert "Critical system issue" in classification.reason
        assert classification.confidence == "Medium"
    
    def test_fallback_classification_client_action(self, classification_agent, sample_alert):
        """Test fallback classification for client-actionable issues."""
        sample_alert.alert_type = "Disk Space Low"
        sample_alert.description = "User needs to clean up disk space"
        
        classification = classification_agent._fallback_classification(sample_alert)
        
        assert classification.action == "notify_client"
        assert "client action" in classification.reason
        assert classification.confidence == "Medium"
    
    def test_fallback_classification_unknown(self, classification_agent, sample_alert):
        """Test fallback classification for unknown patterns."""
        sample_alert.alert_type = "Unknown Alert"
        sample_alert.description = "Some random alert description"
        
        classification = classification_agent._fallback_classification(sample_alert)
        
        assert classification.action == "ignore"
        assert "No clear classification pattern" in classification.reason
        assert classification.confidence == "Low"
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_classify_alert_success(self, mock_boto_client, classification_agent, sample_alert):
        """Test successful alert classification."""
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{
                'text': '{"action": "reboot", "reason": "System needs restart", "confidence": "High"}'
            }]
        }).encode()
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock
        
        # Initialize agent
        await classification_agent.initialize()
        
        # Test classification
        classification = await classification_agent.classify_alert(sample_alert)
        
        assert classification.action == "reboot"
        assert classification.reason == "System needs restart"
        assert classification.confidence == "High"
    
    @pytest.mark.asyncio
    @patch('boto3.client')
    async def test_classify_alert_failure(self, mock_boto_client, classification_agent, sample_alert):
        """Test alert classification failure handling."""
        # Mock Bedrock failure
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = Exception("API Error")
        mock_boto_client.return_value = mock_bedrock
        
        # Initialize agent
        await classification_agent.initialize()
        
        # Test classification
        classification = await classification_agent.classify_alert(sample_alert)
        
        assert classification.action == "ignore"
        assert "Classification failed" in classification.reason
        assert classification.confidence == "Low"
    
    @pytest.mark.asyncio
    async def test_classify_with_fallback_success(self, classification_agent, sample_alert):
        """Test classify_with_fallback when AI succeeds."""
        with patch.object(classification_agent, 'classify_alert') as mock_classify:
            expected_classification = Classification(
                action="reboot",
                reason="AI classification successful",
                confidence="High"
            )
            mock_classify.return_value = expected_classification
            
            result = await classification_agent.classify_with_fallback(sample_alert)
            
            assert result == expected_classification
            mock_classify.assert_called_once_with(sample_alert)
    
    @pytest.mark.asyncio
    async def test_classify_with_fallback_failure(self, classification_agent, sample_alert):
        """Test classify_with_fallback when AI fails."""
        with patch.object(classification_agent, 'classify_alert') as mock_classify:
            mock_classify.side_effect = Exception("AI Error")
            
            result = await classification_agent.classify_with_fallback(sample_alert)
            
            # Should use fallback classification
            assert result.action == "reboot"  # Based on alert type
            assert result.confidence == "Medium"