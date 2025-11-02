import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from scraping.ninja_scraper import ScrapingAgent
from models.alert import Alert


@pytest.fixture
def scraping_agent():
    """Create a scraping agent for testing."""
    return ScrapingAgent()


class TestScrapingAgent:
    """Test cases for ScrapingAgent."""
    
    @pytest.mark.asyncio
    @patch('playwright.async_api.async_playwright')
    async def test_initialize_success(self, mock_playwright, scraping_agent):
        """Test successful agent initialization."""
        # Mock Playwright components
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_chromium = AsyncMock()
        mock_chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium = mock_chromium
        mock_playwright.return_value.start.return_value = mock_playwright_instance
        
        # Test initialization
        await scraping_agent.initialize()
        
        assert scraping_agent.playwright is not None
        assert scraping_agent.browser is not None
        assert scraping_agent.page is not None
    
    @pytest.mark.asyncio
    async def test_login_success(self, scraping_agent):
        """Test successful login to NinjaRMM."""
        # Mock page object
        mock_page = AsyncMock()
        mock_page.url = "https://app.ninjarmm.com/dashboard"
        scraping_agent.page = mock_page
        
        # Test login
        result = await scraping_agent.login("test_user", "test_pass")
        
        assert result is True
        assert scraping_agent.is_logged_in is True
        
        # Verify page interactions
        mock_page.goto.assert_called_once()
        mock_page.wait_for_selector.assert_called_once()
        mock_page.fill.assert_called()
        mock_page.click.assert_called()
    
    @pytest.mark.asyncio
    async def test_login_failure(self, scraping_agent):
        """Test login failure handling."""
        # Mock page object that fails
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network error")
        scraping_agent.page = mock_page
        
        # Test login failure
        result = await scraping_agent.login("test_user", "test_pass")
        
        assert result is False
        assert scraping_agent.is_logged_in is False
    
    @pytest.mark.asyncio
    async def test_scrape_alerts_not_logged_in(self, scraping_agent):
        """Test scraping alerts when not logged in."""
        scraping_agent.is_logged_in = False
        
        with pytest.raises(Exception, match="Must be logged in"):
            await scraping_agent.scrape_alerts()
    
    @pytest.mark.asyncio
    async def test_scrape_generic_alerts(self, scraping_agent):
        """Test generic alert scraping (fallback method)."""
        # Mock page object
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html>Mock page content</html>"
        scraping_agent.page = mock_page
        scraping_agent.is_logged_in = True
        
        # Test scraping
        alerts = await scraping_agent._scrape_generic_alerts(5)
        
        assert len(alerts) == 5
        assert all(isinstance(alert, Alert) for alert in alerts)
        
        # Check first alert structure
        first_alert = alerts[0]
        assert first_alert.device_name == "SERVER-01"
        assert first_alert.alert_type == "Pending Reboot"
        assert first_alert.severity == "High"
    
    @pytest.mark.asyncio
    async def test_extract_alert_data_valid(self, scraping_agent):
        """Test extracting alert data from DOM element."""
        # Mock DOM element
        mock_element = AsyncMock()
        mock_element.text_content.return_value = """
        SERVER-01
        Pending Reboot
        System requires restart after Windows updates
        Additional details here
        """
        
        # Test extraction
        alert = await scraping_agent._extract_alert_data(mock_element, 0)
        
        assert alert is not None
        assert alert.device_name == "SERVER-01"
        assert alert.alert_type == "Pending Reboot"
        assert "System requires restart" in alert.description
        assert alert.severity in ["Critical", "High", "Medium", "Low"]
    
    @pytest.mark.asyncio
    async def test_extract_alert_data_empty(self, scraping_agent):
        """Test extracting alert data from empty element."""
        # Mock empty DOM element
        mock_element = AsyncMock()
        mock_element.text_content.return_value = ""
        
        # Test extraction
        alert = await scraping_agent._extract_alert_data(mock_element, 0)
        
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_scrape_alerts_with_elements(self, scraping_agent):
        """Test scraping alerts when elements are found."""
        # Mock page and elements
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.text_content.return_value = "SERVER-01\nPending Reboot\nSystem needs restart"
        
        # First selector fails, second succeeds
        mock_page.query_selector_all.side_effect = [
            [],  # First selector returns empty
            [mock_element, mock_element],  # Second selector returns elements
        ]
        
        scraping_agent.page = mock_page
        scraping_agent.is_logged_in = True
        
        # Test scraping
        alerts = await scraping_agent.scrape_alerts(2)
        
        assert len(alerts) == 2
        assert all(isinstance(alert, Alert) for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, scraping_agent):
        """Test agent cleanup."""
        # Mock components
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        
        scraping_agent.page = mock_page
        scraping_agent.browser = mock_browser
        scraping_agent.playwright = mock_playwright
        
        # Test cleanup
        await scraping_agent.cleanup()
        
        # Verify cleanup calls
        mock_page.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_with_errors(self, scraping_agent):
        """Test cleanup handling errors gracefully."""
        # Mock components that raise errors
        mock_page = AsyncMock()
        mock_page.close.side_effect = Exception("Close error")
        
        scraping_agent.page = mock_page
        scraping_agent.browser = None  # Missing browser
        scraping_agent.playwright = None  # Missing playwright
        
        # Test cleanup - should not raise exception
        await scraping_agent.cleanup()
        
        # Should have attempted to close page despite error
        mock_page.close.assert_called_once()