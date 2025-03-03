"""Lead analysis and reporting tool for the Milestone Lead Generator."""

import json
import os
import logging
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple

from storage import DataStorage

logger = logging.getLogger(__name__)

class LeadAnalyzer:
    """Analyzes leads data and generates reports."""
    
    def __init__(self):
        self.storage = DataStorage()
    
    def generate_company_report(self, company_name: str) -> Dict[str, Any]:
        """Generate detailed report for a specific company."""
        # Load all leads
        all_leads = self.storage.load_high_value_leads(limit=10000)
        
        # Filter leads for this company
        company_leads = [lead for lead in all_leads if lead.get("company_name", "").lower() == company_name.lower()]
        
        if not company_leads:
            return {"status": "No leads found for company", "company": company_name}
        
        # Sort leads by timestamp
        company_leads.sort(key=lambda x: x.get("timestamp", 0))
        
        # Generate report
        report = {
            "company_name": company_name,
            "lead_count": len(company_leads),
            "first_seen": datetime.fromtimestamp(company_leads[0].get("timestamp", 0)/1000).strftime("%Y-%m-%d"),
            "last_seen": datetime.fromtimestamp(company_leads[-1].get("timestamp", 0)/1000).strftime("%Y-%m-%d"),
            "average_sentiment": sum(lead.get("sentiment", 0) for lead in company_leads) / len(company_leads),
            "milestone_types": {},
            "leads": []
        }
        
        # Count milestone types
        for lead in company_leads:
            milestone_type = lead.get("milestone_details", {}).get("milestone_type", "unknown")
            if milestone_type not in report["milestone_types"]:
                report["milestone_types"][milestone_type] = 0
            report["milestone_types"][milestone_type] += 1
        
        # Add lead details
        for lead in company_leads:
            report["leads"].append({
                "date": datetime.fromtimestamp(lead.get("timestamp", 0)/1000).strftime("%Y-%m-%d"),
                "source": lead.get("source", "unknown"),
                "url": lead.get("url", ""),
                "sentiment": lead.get("sentiment", 0),
                "milestone_type": lead.get("milestone_details", {}).get("milestone_type", "unknown"),
                "milestone_description": lead.get("milestone_details", {}).get("milestone_description", ""),
                "text_snippet": lead.get("text", "")[:100] + "..." if lead.get("text", "") else ""
            })
        
        return report
    
    def generate_trend_report(self, days: int = 90) -> Dict[str, Any]:
        """Generate trend report for the specified number of days."""
        # Load all leads
        all_leads = self.storage.load_high_value_leads(limit=10000)
        
        # Calculate cutoff date
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        cutoff_timestamp = int(cutoff.timestamp() * 1000)
        
        # Filter leads from the specified period
        recent_leads = [lead for lead in all_leads if lead.get("timestamp", 0) >= cutoff_timestamp]
        
        if not recent_leads:
            return {"status": "No leads found in the specified period"}
        
        # Group leads by week
        weeks = {}
        for lead in recent_leads:
            timestamp = lead.get("timestamp", 0)
            week_start = datetime.fromtimestamp(timestamp/1000).strftime("%Y-%W")
            if week_start not in weeks:
                weeks[week_start] = []
            weeks[week_start].append(lead)
        
        # Group by milestone type
        milestone_types = {}
        for lead in recent_leads:
            milestone_type = lead.get("milestone_details", {}).get("milestone_type", "unknown")
            if milestone_type not in milestone_types:
                milestone_types[milestone_type] = []
            milestone_types[milestone_type].append(lead)
        
        # Generate trend report
        report = {
            "period": f"Last {days} days",
            "total_leads": len(recent_leads),
            "weekly_trends": {},
            "milestone_types": {},
            "top_companies": []
        }
        
        # Add weekly trends
        for week, week_leads in sorted(weeks.items()):
            report["weekly_trends"][week] = len(week_leads)
        
        # Add milestone type distribution
        for milestone_type, type_leads in milestone_types.items():
            report["milestone_types"][milestone_type] = len(type_leads)
        
        # Count leads by company
        companies = {}
        for lead in recent_leads:
            company_name = lead.get("company_name", "Unknown")
            if company_name not in companies:
                companies[company_name] = []
            companies[company_name].append(lead)
        
        # Add top companies
        for company, company_leads in sorted(companies.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            report["top_companies"].append({
                "name": company,
                "lead_count": len(company_leads)
            })
        
        return report
    
    def visualize_trends(self, days: int = 90) -> str:
        """Generate visualization of trends and save as image."""
        trend_report = self.generate_trend_report(days)
        
        if trend_report.get("status", "").startswith("No leads"):
            return "No leads available for visualization"
        
        # Create figure with multiple subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
        
        # Plot 1: Weekly trends
        weekly_trends = trend_report.get("weekly_trends", {})
        weeks = list(weekly_trends.keys())
        counts = list(weekly_trends.values())
        
        ax1.bar(weeks, counts)
        ax1.set_title(f"Lead Volume by Week (Last {days} Days)")
        ax1.set_xlabel("Week")
        ax1.set_ylabel("Number of Leads")
        plt.setp(ax1.get_xticklabels(), rotation=45)
        
        # Plot 2: Milestone type distribution
        milestone_types = trend_report.get("milestone_types", {})
        types = list(milestone_types.keys())
        type_counts = list(milestone_types.values())
        
        ax2.pie(type_counts, labels=types, autopct='%1.1f%%')
        ax2.set_title("Distribution by Milestone Type")
        
        # Adjust layout and save
        plt.tight_layout()
        filename = f"trend_report_{datetime.now().strftime('%Y%m%d')}.png"
        filepath = os.path.join("data", filename)
        plt.savefig(filepath)
        plt.close()
        
        return filepath


def main():
    """Main entry point for lead analysis."""
    parser = argparse.ArgumentParser(description="Milestone Lead Analyzer")
    parser.add_argument(
        "--mode", 
        choices=["company", "trends", "visualize"],
        default="trends",
        help="Report mode: company (detailed company report), trends (general trends), or visualize (generate charts)"
    )
    parser.add_argument(
        "--company", 
        type=str,
        help="Company name for company report"
    )
    parser.add_argument(
        "--days", 
        type=int, 
        default=90,
        help="Number of days to include in trend analysis"
    )
    
    args = parser.parse_args()
    analyzer = LeadAnalyzer()
    
    if args.mode == "company":
        if not args.company:
            print("Error: Company name required for company report")
            return
        report = analyzer.generate_company_report(args.company)
        print(json.dumps(report, indent=2))
    elif args.mode == "trends":
        report = analyzer.generate_trend_report(days=args.days)
        print(json.dumps(report, indent=2))
    elif args.mode == "visualize":
        filepath = analyzer.visualize_trends(days=args.days)
        print(f"Visualization saved to: {filepath}")


if __name__ == "__main__":
    main()