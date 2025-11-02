import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from models.alert import Alert
from models.classification import Classification
from actions.executor import ActionAgent


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
        raw_text="TEST-SERVER-01: Pending Reboot - System requires restart"
    )


@pytest.fixture
def action_agent():
    """Create an action agent for testing."""
    return ActionAgent()


class TestActionAgent:
    """Test cases for ActionAgent."""
    
    @pytest.mark.asyncio
    async def test_execute_reboot_action(self, action_agent, sample_alert):
        """Test reboot action execution."""
        classification = Classification(
            action="reboot",
            reason="System needs restart",
            confidence="High"
        )
        
        action_taken, status = await action_agent._execute_reboot(sample_alert)
        
        assert action_taken == "reboot_simulated"
        assert status == "success"
    
    @pytest.mark.asyncio
    async def test_execute_notify_client_action(self, action_agent, sample_alert):
        """Test client notification action."""
        classification = Classification(
            action="notify_client",
            reason="User action required",
            confidence="High"
        )
        
        action_taken, status = await action_agent._notify_client(sample_alert, classification)
        
        assert action_taken == "client_notified"
        assert status == "success"
    
    @pytest.mark.asyncio
    async def test_execute_ignore_action(self, action_agent, sample_alert):
        """Test ignore action execution."""
        classification = Classification(
            action="ignore",
            reason="False positive alert",
            confidence="High"
        )
        
        action_taken, status = await action_agent._ignore_alert(sample_alert, classification)
        
        assert action_taken == "alert_ignored"
        assert status == "success"
    
    @pytest.mark.asyncio
    @patch('requests.Session.post')
    async def test_create_ticket_success(self, mock_post, action_agent, sample_alert):
        """Test successful ticket creation."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        classification = Classification(
            action="create_ticket",
            reason="Complex technical issue",
            confidence="High"
        )
        
        await action_agent.initialize()
        action_taken, status = await action_agent._create_ticket(sample_alert, classification)
        
        assert action_taken == "ticket_created"
        assert status == "success"
        
        # Verify webhook was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check payload structure
        payload = call_args[1]['json']
        assert payload['title'] == f"{sample_alert.alert_type} - {sample_alert.device_name}"
        assert payload['device'] == sample_alert.device_name
        assert payload['alert_id'] == sample_alert.id
    
    @pytest.mark.asyncio
    @patch('requests.Session.post')
    async def test_create_ticket_failure(self, mock_post, action_agent, sample_alert):
        """Test ticket creation failure."""
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        classification = Classification(
            action="create_ticket",
            reason="Complex technical issue",
            confidence="High"
        )
        
        await action_agent.initialize()
        action_taken, status = await action_agent._create_ticket(sample_alert, classification)
        
        assert action_taken == "ticket_failed"
        assert status == "error"
    
    @pytest.mark.asyncio
    async def test_execute_action_dispatch(self, action_agent, sample_alert):
        """Test action execution dispatching."""
        # Test reboot action
        reboot_classification = Classification(
            action="reboot",
            reason="System needs restart",
            confidence="High"
        )
        
        action_taken, status = await action_agent.execute_action(sample_alert, reboot_classification)
        assert action_taken == "reboot_simulated"
        assert status == "success"
        
        # Test ignore action
        ignore_classification = Classification(
            action="ignore",
            reason="False positive",
            confidence="High"
        )
        
        action_taken, status = await action_agent.execute_action(sample_alert, ignore_classification)
        assert action_taken == "alert_ignored"
        assert status == "success"
    
    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, action_agent, sample_alert):
        """Test handling of unknown action types."""
        unknown_classification = Classification(
            action="unknown_action",
            reason="Test unknown action",
            confidence="High"
        )
        
        # This should be caught by validation, but test the executor's handling
        with patch.object(unknown_classification, 'action', 'unknown_action'):
            action_taken, status = await action_agent.execute_action(sample_alert, unknown_classification)
            
            assert action_taken == "unknown_action"
            assert status == "error"
    
    def test_map_severity_to_priority(self, action_agent):
        """Test severity to priority mapping."""
        assert action_agent._map_severity_to_priority("Critical") == "High"
        assert action_agent._map_severity_to_priority("High") == "High"
        assert action_agent._map_severity_to_priority("Medium") == "Medium"
        assert action_agent._map_severity_to_priority("Low") == "Low"
        assert action_agent._map_severity_to_priority("Info") == "Low"
        assert action_agent._map_severity_to_priority("Unknown") == "Medium"  # Default
    
    @pytest.mark.asyncio
    async def test_cleanup(self, action_agent):
        """Test agent cleanup."""
        await action_agent.initialize()
        
        # Verify session exists
        assert action_agent.session is not None
        
        # Test cleanup
        await action_agent.cleanup()
        
        # Session should be closed (we can't easily test this without mocking)