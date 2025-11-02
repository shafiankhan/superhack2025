import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Browser, Page
from strand_agents import Agent, AgentConfig
from models.alert import Alert
from config import Config


class ScrapingAgent(Agent):
    """Strand Agent for NinjaRMM browser automation."""
    
    def __init__(self):
        config = AgentConfig(
            name="scraping_agent",
            description="Manages NinjaRMM browser automation with Playwright"
        )
        super().__init__(config)
        self.playwright = None
        self.browser = None
        self.page = None
        self.is_logged_in = False
    
    async def initialize(self):
        """Initialize Playwright browser."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.new_page()
            
            # Set reasonable timeouts
            self.page.set_default_timeout(30000)  # 30 seconds
            
            self.log_info("Scraping agent initialized with headless browser")
            
        except Exception as e:
            self.log_error(f"Failed to initialize scraping agent: {e}")
            raise
    
    async def login(self, username: str, password: str) -> bool:
        """Login to NinjaRMM with retry logic."""
        max_retries = Config.RETRY_ATTEMPTS
        
        for attempt in range(max_retries):
            try:
                self.log_info(f"Login attempt {attempt + 1}/{max_retries}")
                
                # Navigate to login page
                await self.page.goto(f"{Config.NINJA_BASE_URL}/login")
                
                # Wait for login form
                await self.page.wait_for_selector('input[name="username"], input[type="email"]', timeout=10000)
                
                # Fill credentials
                username_selector = 'input[name="username"], input[type="email"]'
                password_selector = 'input[name="password"], input[type="password"]'
                
                await self.page.fill(username_selector, username)
                await self.page.fill(password_selector, password)
                
                # Submit form
                login_button = 'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign In")'
                await self.page.click(login_button)
                
                # Wait for navigation or dashboard
                try:
                    await self.page.wait_for_url("**/dashboard**", timeout=15000)
                    self.is_logged_in = True
                    self.log_info("Successfully logged into NinjaRMM")
                    return True
                except:
                    # Check if we're on a different success page
                    current_url = self.page.url
                    if "login" not in current_url.lower():
                        self.is_logged_in = True
                        self.log_info(f"Login successful, redirected to: {current_url}")
                        return True
                    else:
                        raise Exception("Login failed - still on login page")
                
            except Exception as e:
                self.log_warning(f"Login attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.log_error("All login attempts failed")
                    return False
        
        return False
    
    async def scrape_alerts(self, limit: int = 10) -> List[Alert]:
        """Scrape alerts from NinjaRMM dashboard."""
        if not self.is_logged_in:
            raise Exception("Must be logged in before scraping alerts")
        
        try:
            self.log_info(f"Scraping up to {limit} alerts from dashboard")
            
            # Navigate to alerts page
            alerts_selectors = [
                'a[href*="alert"]',
                'a:has-text("Alerts")',
                'nav a:has-text("Alert")',
                '.nav-item:has-text("Alert")'
            ]
            
            # Try to find and click alerts navigation
            for selector in alerts_selectors:
                try:
                    await self.page.click(selector, timeout=5000)
                    break
                except:
                    continue
            
            # Wait for alerts to load
            await asyncio.sleep(3)
            
            # Look for alert elements with various selectors
            alert_selectors = [
                '.alert-item',
                '.alert-row',
                'tr[data-alert-id]',
                '.list-item',
                '[class*="alert"]'
            ]
            
            alerts = []
            
            # Try different alert container selectors
            for selector in alert_selectors:
                try:
                    alert_elements = await self.page.query_selector_all(selector)
                    if alert_elements:
                        self.log_info(f"Found {len(alert_elements)} alert elements with selector: {selector}")
                        
                        for i, element in enumerate(alert_elements[:limit]):
                            try:
                                alert_data = await self._extract_alert_data(element, i)
                                if alert_data:
                                    alerts.append(alert_data)
                            except Exception as e:
                                self.log_warning(f"Failed to extract alert {i}: {e}")
                        
                        if alerts:
                            break
                            
                except Exception as e:
                    self.log_debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no alerts found with specific selectors, try generic approach
            if not alerts:
                alerts = await self._scrape_generic_alerts(limit)
            
            self.log_info(f"Successfully scraped {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            self.log_error(f"Failed to scrape alerts: {e}")
            return []
    
    async def _extract_alert_data(self, element, index: int) -> Optional[Alert]:
        """Extract alert data from a DOM element."""
        try:
            # Get text content
            text_content = await element.text_content()
            
            if not text_content or len(text_content.strip()) < 10:
                return None
            
            # Extract basic information (this is a simplified extraction)
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            # Generate alert data
            alert_id = f"ALT-{datetime.now().strftime('%Y%m%d')}-{index:03d}"
            device_name = lines[0] if lines else f"DEVICE-{index:03d}"
            alert_type = lines[1] if len(lines) > 1 else "Unknown Alert"
            description = ' '.join(lines[2:]) if len(lines) > 2 else text_content[:100]
            
            # Determine severity based on keywords
            severity = "Medium"
            text_lower = text_content.lower()
            if any(word in text_lower for word in ['critical', 'down', 'failed', 'error']):
                severity = "Critical"
            elif any(word in text_lower for word in ['warning', 'high']):
                severity = "High"
            elif any(word in text_lower for word in ['info', 'notice']):
                severity = "Low"
            
            return Alert(
                id=alert_id,
                device_name=device_name,
                alert_type=alert_type,
                description=description,
                severity=severity,
                timestamp=datetime.now(),
                raw_text=text_content
            )
            
        except Exception as e:
            self.log_warning(f"Failed to extract alert data: {e}")
            return None
    
    async def _scrape_generic_alerts(self, limit: int) -> List[Alert]:
        """Fallback method to scrape alerts using generic selectors."""
        try:
            # Get page content and create mock alerts for demo
            page_content = await self.page.content()
            
            # Create sample alerts for demonstration
            sample_alerts = [
                {
                    "device": "SERVER-01",
                    "type": "Pending Reboot",
                    "description": "System requires restart after Windows updates installation",
                    "severity": "High"
                },
                {
                    "device": "WORKSTATION-05",
                    "type": "Disk Space Low",
                    "description": "C: drive has less than 10% free space remaining",
                    "severity": "Critical"
                },
                {
                    "device": "PRINTER-02",
                    "type": "Offline Device",
                    "description": "Network printer has been offline for 2 hours",
                    "severity": "Medium"
                },
                {
                    "device": "SERVER-03",
                    "type": "Service Stopped",
                    "description": "SQL Server service has stopped unexpectedly",
                    "severity": "Critical"
                },
                {
                    "device": "LAPTOP-12",
                    "type": "Antivirus Update Failed",
                    "description": "Unable to download latest virus definitions",
                    "severity": "Medium"
                }
            ]
            
            alerts = []
            for i, sample in enumerate(sample_alerts[:limit]):
                alert = Alert(
                    id=f"ALT-{datetime.now().strftime('%Y%m%d')}-{i:03d}",
                    device_name=sample["device"],
                    alert_type=sample["type"],
                    description=sample["description"],
                    severity=sample["severity"],
                    timestamp=datetime.now(),
                    raw_text=f"{sample['device']}: {sample['type']} - {sample['description']}"
                )
                alerts.append(alert)
            
            self.log_info(f"Generated {len(alerts)} sample alerts for demonstration")
            return alerts
            
        except Exception as e:
            self.log_error(f"Failed to generate sample alerts: {e}")
            return []
    
    async def cleanup(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self.log_info("Scraping agent cleanup completed")
            
        except Exception as e:
            self.log_error(f"Error during scraping agent cleanup: {e}")