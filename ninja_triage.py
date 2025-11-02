#!/usr/bin/env python3
"""
NinjaTriage AI - Automated Alert Triage System
Main controller using Strand Agents framework
"""

import asyncio
import argparse
import json
import signal
import sys
from datetime import datetime
from typing import List, Optional
from strand_agents import AgentOrchestrator

from config import Config
from models.alert import Alert
from auth.credential_manager import CredentialAgent
from scraping.ninja_scraper import ScrapingAgent
from ai.alert_classifier import ClassificationAgent
from actions.executor import ActionAgent
from utils.logger import LoggingAgent


class NinjaTriageOrchestrator:
    """Main orchestrator for NinjaTriage AI using Strand Agents."""
    
    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.orchestrator = AgentOrchestrator()
        
        # Initialize agents
        self.credential_agent = CredentialAgent()
        self.scraping_agent = ScrapingAgent()
        self.classification_agent = ClassificationAgent()
        self.action_agent = ActionAgent()
        self.logging_agent = LoggingAgent()
        
        # Register agents with orchestrator
        self.orchestrator.register_agent(self.credential_agent)
        self.orchestrator.register_agent(self.scraping_agent)
        self.orchestrator.register_agent(self.classification_agent)
        self.orchestrator.register_agent(self.action_agent)
        self.orchestrator.register_agent(self.logging_agent)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.shutdown_requested = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Shutdown signal received ({signum}). Finishing current alert and exiting...")
        self.shutdown_requested = True
    
    async def initialize(self):
        """Initialize all agents."""
        try:
            print("🚀 Initializing NinjaTriage AI...")
            
            # Validate configuration
            Config.validate(demo_mode=self.demo_mode)
            
            # Initialize orchestrator and agents
            await self.orchestrator.initialize()
            
            print("✅ All agents initialized successfully")
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            raise
    
    async def run(self):
        """Main execution loop."""
        try:
            await self.initialize()
            
            if self.demo_mode:
                await self._run_demo_mode()
            else:
                await self._run_production_mode()
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            await self.logging_agent.log_summary()
            raise
        finally:
            await self._cleanup()
    
    async def _run_demo_mode(self):
        """Run in demo mode with pre-loaded alerts."""
        print("\n🎬 Running in DEMO mode with sample alerts...")
        
        # Load demo alerts
        alerts = await self._load_demo_alerts()
        
        if not alerts:
            print("❌ No demo alerts found")
            return
        
        print(f"📋 Processing {len(alerts)} demo alerts...\n")
        
        # Process alerts
        await self._process_alerts(alerts)
        
        # Generate summary
        await self._generate_summary()
    
    async def _run_production_mode(self):
        """Run in production mode with live NinjaRMM data."""
        print("\n🔐 Retrieving credentials...")
        
        # Get credentials
        credentials = await self.credential_agent.get_ninja_credentials()
        
        print("🌐 Logging into NinjaRMM...")
        
        # Login to NinjaRMM
        login_success = await self.scraping_agent.login(
            credentials['username'], 
            credentials['password']
        )
        
        if not login_success:
            raise Exception("Failed to login to NinjaRMM")
        
        print("📋 Scraping alerts from dashboard...")
        
        # Scrape alerts
        alerts = await self.scraping_agent.scrape_alerts(Config.ALERT_LIMIT)
        
        if not alerts:
            print("ℹ️  No alerts found to process")
            return
        
        print(f"🔍 Processing {len(alerts)} alerts...\n")
        
        # Process alerts
        await self._process_alerts(alerts)
        
        # Generate summary
        await self._generate_summary()
    
    async def _load_demo_alerts(self) -> List[Alert]:
        """Load alerts from demo data file."""
        try:
            with open('data/demo_alerts.json', 'r') as f:
                demo_data = json.load(f)
            
            alerts = []
            for data in demo_data:
                alert = Alert.from_dict(data)
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            print(f"❌ Failed to load demo alerts: {e}")
            return []
    
    async def _process_alerts(self, alerts: List[Alert]):
        """Process a list of alerts through the triage pipeline."""
        for i, alert in enumerate(alerts, 1):
            if self.shutdown_requested:
                print(f"\n🛑 Shutdown requested, stopping after {i-1} alerts")
                break
            
            print(f"🔍 [{i}/{len(alerts)}] Processing: {alert.device_name} - {alert.alert_type}")
            
            start_time = datetime.now()
            
            try:
                # Classify alert with AI
                classification = await self.classification_agent.classify_with_fallback(alert)
                
                # Execute action
                action_taken, status = await self.action_agent.execute_action(alert, classification)
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Log decision
                await self.logging_agent.log_decision(
                    alert=alert,
                    classification=classification,
                    action_taken=action_taken,
                    execution_status=status,
                    processing_time_ms=int(processing_time)
                )
                
                print(f"   ✅ Completed in {processing_time:.0f}ms\n")
                
                # Small delay between alerts for demo effect
                if self.demo_mode:
                    await asyncio.sleep(1)
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                print(f"   ❌ Error: {e}")
                
                # Log error
                await self.logging_agent.log_decision(
                    alert=alert,
                    classification=None,
                    action_taken="processing_failed",
                    execution_status="error",
                    processing_time_ms=int(processing_time),
                    error_message=str(e)
                )
    
    async def _generate_summary(self):
        """Generate and display session summary."""
        print("📊 Generating session summary...")
        
        summary = await self.logging_agent.log_summary()
        
        if summary:
            print("\n" + "="*60)
            print("📈 SESSION SUMMARY")
            print("="*60)
            print(f"Alerts Processed: {summary['total_alerts_processed']}")
            print(f"Session Duration: {summary['session_duration_seconds']:.1f} seconds")
            print(f"Errors: {summary['errors_encountered']}")
            
            if summary['actions_breakdown']:
                print("\nActions Taken:")
                for action, count in summary['actions_breakdown'].items():
                    print(f"  • {action.replace('_', ' ').title()}: {count}")
            
            time_savings = summary['time_savings']
            print(f"\nTime Savings:")
            print(f"  • Per Alert: {time_savings['per_alert_seconds']} seconds saved")
            print(f"  • Total Saved: {time_savings['total_saved_minutes']} minutes")
            print(f"  • Daily Projection: {time_savings['daily_projection_minutes']} minutes/day")
            
            print("="*60)
    
    async def _cleanup(self):
        """Cleanup all agents and resources."""
        try:
            print("\n🧹 Cleaning up resources...")
            await self.orchestrator.shutdown()
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NinjaTriage AI - Automated Alert Triage")
    parser.add_argument(
        "--demo", 
        action="store_true", 
        help="Run in demo mode with sample alerts"
    )
    
    args = parser.parse_args()
    
    print("🥷 NinjaTriage AI - Automated Alert Triage System")
    print("=" * 50)
    
    orchestrator = NinjaTriageOrchestrator(demo_mode=args.demo)
    
    try:
        await orchestrator.run()
        print("\n✅ NinjaTriage AI completed successfully")
        
    except Exception as e:
        print(f"\n❌ NinjaTriage AI failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())