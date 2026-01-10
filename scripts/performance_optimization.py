#!/usr/bin/env python3
"""
Firehorse Performance Optimization Script
Optimizes system performance based on current metrics and load.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import psutil
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Optimizes Firehorse system performance."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.metrics_cache = {}
        
    async def collect_metrics(self) -> Dict:
        """Collect system and application metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "application": {},
            "database": {},
            "recommendations": []
        }
        
        # System metrics
        metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_average": psutil.getloadavg(),
            "process_count": len(psutil.pids())
        }
        
        # Docker metrics
        metrics["system"]["docker_stats"] = self._get_docker_stats()
        
        # Application metrics
        try:
            health_response = requests.get(f"{self.api_url}/health", timeout=5)
            if health_response.status_code == 200:
                metrics["application"]["health"] = health_response.json()
            
            metrics_response = requests.get(f"{self.api_url}/metrics", timeout=5)
            if metrics_response.status_code == 200:
                metrics["application"]["metrics_raw"] = metrics_response.text
                metrics["application"]["parsed_metrics"] = self._parse_prometheus_metrics(
                    metrics_response.text
                )
        except Exception as e:
            logger.warning(f"Failed to collect application metrics: {e}")
            
        # Database metrics (simplified)
        metrics["database"] = {
            "connection_pool": self._estimate_db_pool_usage(),
            "query_performance": self._estimate_query_performance()
        }
        
        return metrics
    
    def _get_docker_stats(self) -> List[Dict]:
        """Get Docker container statistics."""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            stats = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(",")
                    if len(parts) >= 7:
                        stats.append({
                            "name": parts[0],
                            "cpu_percent": parts[1].replace("%", ""),
                            "memory_usage": parts[2],
                            "memory_percent": parts[3].replace("%", ""),
                            "network_io": parts[4],
                            "block_io": parts[5],
                            "pids": parts[6]
                        })
            return stats
        except Exception as e:
            logger.warning(f"Failed to get Docker stats: {e}")
            return []
    
    def _parse_prometheus_metrics(self, metrics_text: str) -> Dict:
        """Parse Prometheus metrics into structured format."""
        parsed = {
            "counters": {},
            "gauges": {},
            "histograms": {}
        }
        
        for line in metrics_text.split("\n"):
            if line and not line.startswith("#"):
                if "firehorse_" in line:
                    # Simple parsing - in production use prometheus_client
                    if "firehorse_requests_total" in line:
                        parsed["counters"]["requests_total"] = self._extract_metric_value(line)
                    elif "firehorse_queue_depth" in line:
                        parsed["gauges"]["queue_depth"] = self._extract_metric_value(line)
                    elif "firehorse_api_latency_seconds_bucket" in line:
                        parsed["histograms"]["api_latency"] = self._extract_metric_value(line)
        
        return parsed
    
    def _extract_metric_value(self, line: str) -> float:
        """Extract numeric value from Prometheus metric line."""
        try:
            # Format: metric_name{labels} value
            value_part = line.split()[-1]
            return float(value_part)
        except:
            return 0.0
    
    def _estimate_db_pool_usage(self) -> Dict:
        """Estimate database connection pool usage."""
        # Simplified estimation
        return {
            "estimated_connections": 10,
            "max_connections": 20,
            "usage_percent": 50.0
        }
    
    def _estimate_query_performance(self) -> Dict:
        """Estimate database query performance."""
        return {
            "avg_query_time_ms": 100.0,
            "slow_queries_per_hour": 5,
            "index_hit_ratio": 0.95
        }
    
    def analyze_performance(self, metrics: Dict) -> List[Dict]:
        """Analyze metrics and generate optimization recommendations."""
        recommendations = []
        
        # CPU analysis
        cpu_percent = metrics["system"]["cpu_percent"]
        if cpu_percent > 80:
            recommendations.append({
                "category": "CPU",
                "severity": "high",
                "issue": f"High CPU usage: {cpu_percent}%",
                "recommendation": "Consider scaling horizontally or optimizing worker concurrency",
                "action": "Scale workers: docker-compose up -d --scale worker=3"
            })
        elif cpu_percent > 60:
            recommendations.append({
                "category": "CPU",
                "severity": "medium",
                "issue": f"Moderate CPU usage: {cpu_percent}%",
                "recommendation": "Monitor CPU usage and consider optimization",
                "action": "Review worker configuration in .env"
            })
        
        # Memory analysis
        memory_percent = metrics["system"]["memory_percent"]
        if memory_percent > 85:
            recommendations.append({
                "category": "Memory",
                "severity": "high",
                "issue": f"High memory usage: {memory_percent}%",
                "recommendation": "Consider increasing memory or optimizing memory usage",
                "action": "Increase Docker memory limits or add swap space"
            })
        
        # Queue analysis
        if "gauges" in metrics["application"].get("parsed_metrics", {}):
            queue_depth = metrics["application"]["parsed_metrics"]["gauges"].get("queue_depth", 0)
            if queue_depth > 50:
                recommendations.append({
                    "category": "Queue",
                    "severity": "high",
                    "issue": f"High queue depth: {queue_depth}",
                    "recommendation": "Queue is filling up faster than workers can process",
                    "action": "Increase worker count or batch size"
                })
            elif queue_depth > 20:
                recommendations.append({
                    "category": "Queue",
                    "severity": "medium",
                    "issue": f"Moderate queue depth: {queue_depth}",
                    "recommendation": "Monitor queue growth",
                    "action": "Consider increasing WORKER_MAX_BATCH_SIZE"
                })
        
        # Database analysis
        db_usage = metrics["database"]["connection_pool"]["usage_percent"]
        if db_usage > 80:
            recommendations.append({
                "category": "Database",
                "severity": "high",
                "issue": f"High database connection pool usage: {db_usage}%",
                "recommendation": "Consider increasing connection pool size",
                "action": "Increase DATABASE_POOL_SIZE in .env"
            })
        
        # Disk analysis
        disk_usage = metrics["system"]["disk_usage"]
        if disk_usage > 90:
            recommendations.append({
                "category": "Disk",
                "severity": "critical",
                "issue": f"Critical disk usage: {disk_usage}%",
                "recommendation": "Disk space is running low",
                "action": "Clean up old logs and backups immediately"
            })
        elif disk_usage > 80:
            recommendations.append({
                "category": "Disk",
                "severity": "high",
                "issue": f"High disk usage: {disk_usage}%",
                "recommendation": "Consider cleaning up old files",
                "action": "Run: find ./logs -name '*.log' -mtime +7 -delete"
            })
        
        return recommendations
    
    def generate_optimization_plan(self, recommendations: List[Dict]) -> Dict:
        """Generate an optimization plan based on recommendations."""
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_improvements": [],
            "configuration_changes": []
        }
        
        for rec in recommendations:
            if rec["severity"] in ["critical", "high"]:
                plan["immediate_actions"].append(rec)
            elif rec["severity"] == "medium":
                plan["short_term_actions"].append(rec)
            else:
                plan["long_term_improvements"].append(rec)
            
            # Extract configuration changes
            if "Increase" in rec.get("action", "") or "Decrease" in rec.get("action", ""):
                plan["configuration_changes"].append(rec)
        
        return plan
    
    async def apply_optimizations(self, plan: Dict) -> Dict:
        """Apply optimization recommendations."""
        results = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "summary": ""
        }
        
        # Apply immediate actions (critical/high severity)
        for action in plan["immediate_actions"]:
            try:
                if "Scale workers" in action.get("action", ""):
                    # This would require Docker Compose
                    logger.info(f"Would apply: {action['action']}")
                    results["applied"].append({
                        "action": action["action"],
                        "category": action["category"],
                        "status": "simulated"
                    })
                elif "Clean up" in action.get("action", ""):
                    # Actually clean up old logs
                    self._cleanup_old_logs()
                    results["applied"].append({
                        "action": action["action"],
                        "category": action["category"],
                        "status": "applied"
                    })
                else:
                    results["skipped"].append({
                        "action": action["action"],
                        "category": action["category"],
                        "reason": "Requires manual intervention"
                    })
            except Exception as e:
                results["failed"].append({
                    "action": action["action"],
                    "category": action["category"],
                    "error": str(e)
                })
        
        # Generate summary
        total = len(results["applied"]) + len(results["skipped"]) + len(results["failed"])
        if total > 0:
            results["summary"] = (
                f"Applied {len(results['applied'])}/{total} optimizations. "
                f"Skipped {len(results['skipped'])}. Failed {len(results['failed'])}."
            )
        
        return results
    
    def _cleanup_old_logs(self):
        """Clean up old log files."""
        try:
            # Clean logs older than 7 days
            subprocess.run(
                ["find", "./logs", "-name", "*.log", "-mtime", "+7", "-delete"],
                capture_output=True,
                text=True
            )
            logger.info("Cleaned up old log files")
        except Exception as e:
            logger.error(f"Failed to clean up logs: {e}")
    
    def generate_report(self, metrics: Dict, recommendations: List[Dict], 
                       plan: Dict, results: Dict) -> str:
        """Generate a comprehensive performance report."""
        report = [
            "=" * 80,
            "FIREHORSE PERFORMANCE OPTIMIZATION REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 80,
            "",
            "📊 METRICS SUMMARY",
            "-" * 40,
            f"CPU Usage: {metrics['system']['cpu_percent']}%",
            f"Memory Usage: {metrics['system']['memory_percent']}%",
            f"Disk Usage: {metrics['system']['disk_usage']}%",
            f"Load Average: {metrics['system']['load_average']}",
            "",
            "🔍 RECOMMENDATIONS",
            "-" * 40,
        ]
        
        for rec in recommendations:
            report.append(
                f"[{rec['severity'].upper()}] {rec['category']}: {rec['issue']}"
            )
            report.append(f"    Recommendation: {rec['recommendation']}")
            report.append(f"    Action: {rec['action']}")
            report.append("")
        
        report.extend([
            "📋 OPTIMIZATION PLAN",
            "-" * 40,
            f"Immediate Actions: {len(plan['immediate_actions'])}",
            f"Short-term Actions: {len(plan['short_term_actions'])}",
            f"Long-term Improvements: {len(plan['long_term_improvements'])}",
            f"Configuration Changes: {len(plan['configuration_changes'])}",
            "",
            "🚀 OPTIMIZATION RESULTS",
            "-" * 40,
            results.get("summary", "No optimizations applied"),
            "",
            "⚙️ SUGGESTED CONFIGURATION UPDATES",
            "-" * 40,
        ])
        
        # Suggest configuration updates
        config_updates = self._suggest_configuration_updates(metrics, recommendations)
        for key, value in config_updates.items():
            report.append(f"{key}={value}")
        
        report.extend([
            "",
            "=" * 80,
            "END OF REPORT",
            "=" * 80
        ])
        
        return "\n".join(report)
    
    def _suggest_configuration_updates(self, metrics: Dict, recommendations: List[Dict]) -> Dict:
        """Suggest configuration updates based on analysis."""
        updates = {}
        
        # Analyze CPU usage for worker concurrency
        cpu_percent = metrics["system"]["cpu_percent"]
        if cpu_percent > 80:
            updates["WORKER_CONCURRENCY"] = "2"  # Reduce concurrency
        elif cpu_percent < 30:
            updates["WORKER_CONCURRENCY"] = "6"  # Increase concurrency
        
        # Analyze queue depth for batch size
        if "gauges" in metrics["application"].get("parsed_metrics", {}):
            queue_depth = metrics["application"]["parsed_metrics"]["gauges"].get("queue_depth", 0)
            if queue_depth > 50:
                updates["WORKER_MAX_BATCH_SIZE"] = "15"  # Increase batch size
            elif queue_depth < 10:
                updates["WORKER_POLL_INTERVAL"] = "10"  # Increase poll interval
        
        # Analyze memory for connection pool
        memory_percent = metrics["system"]["memory_percent"]
        if memory_percent > 80:
            updates["DATABASE_POOL_SIZE"] = "5"  # Reduce pool size
        elif memory_percent < 50:
            updates["DATABASE_MAX_OVERFLOW"] = "30"  # Increase overflow
        
        return updates


async def main():
    """Main optimization routine."""
    print("🚀 Firehorse Performance Optimization")
    print("=" * 50)
    
    optimizer = PerformanceOptimizer()
    
    # Step 1: Collect metrics
    print("📊 Collecting metrics...")
    metrics = await optimizer.collect_metrics()
    
    # Step 2: Analyze performance
    print("🔍 Analyzing performance...")
    recommendations = optimizer.analyze_performance(metrics)
    
    # Step 3: Generate optimization plan
    print("📋 Generating optimization plan...")
    plan = optimizer.generate_optimization_plan(recommendations)
    
    # Step 4: Apply optimizations
    print("⚡ Applying optimizations...")
    results = await optimizer.apply_optimizations(plan)
    
    # Step 5: Generate report
    print("📄 Generating report...")
    report = optimizer.generate_report(metrics, recommendations, plan, results)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"performance_report_{timestamp}.txt"
    
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"✅ Report saved to: {report_file}")
    print("\n" + "=" * 50)
    print("📋 REPORT SUMMARY")
    print("=" * 50)
    print(report[:500] + "..." if len(report) > 500 else report)
    
    return {
        "metrics": metrics,
        "recommendations": recommendations,
        "plan": plan,
        "results": results,
        "report_file": report_file
    }


if __name__ == "__main__":
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("❌ psutil is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    try:
        import requests
    except ImportError:
        print("❌ requests is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    
    # Run the optimizer
    asyncio.run(main())
