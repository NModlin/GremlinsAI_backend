#!/usr/bin/env python3
"""
Load Test Results Analysis Script - Task T3.5

This script analyzes load test results and provides comprehensive
performance insights and recommendations.

Features:
- Historical results comparison
- Performance trend analysis
- Bottleneck identification
- Optimization recommendations
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics

from load_test_config import evaluate_performance, PERFORMANCE_THRESHOLDS


class LoadTestAnalyzer:
    """Analyzes load test results and provides insights."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results = []
    
    def load_results(self, filename: Optional[str] = None):
        """Load test results from file(s)."""
        if filename:
            # Load specific file
            filepath = self.results_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    result = json.load(f)
                    result['filename'] = filename
                    self.results.append(result)
            else:
                print(f"❌ Results file not found: {filepath}")
                return False
        else:
            # Load all results files
            result_files = list(self.results_dir.glob("load_test_results_*.json"))
            
            if not result_files:
                print(f"❌ No results files found in {self.results_dir}")
                return False
            
            for filepath in sorted(result_files):
                try:
                    with open(filepath, 'r') as f:
                        result = json.load(f)
                        result['filename'] = filepath.name
                        self.results.append(result)
                except Exception as e:
                    print(f"⚠️  Error loading {filepath}: {e}")
        
        print(f"✅ Loaded {len(self.results)} test result(s)")
        return True
    
    def analyze_single_result(self, result: Dict[str, Any]):
        """Analyze a single test result."""
        print(f"\n" + "="*80)
        print(f"📊 ANALYSIS: {result.get('filename', 'Unknown')}")
        print(f"="*80)
        
        # Extract metrics
        metrics = result.get('performance_metrics', {})
        summary = result.get('test_summary', {})
        validation = result.get('validation', {})
        
        # Basic test info
        print(f"\n📋 Test Summary:")
        print(f"   Host: {summary.get('host', 'Unknown')}")
        print(f"   Users: {summary.get('concurrent_users', 0):,}")
        print(f"   Duration: {summary.get('test_duration', 0):.1f}s")
        print(f"   Total Requests: {summary.get('total_requests', 0):,}")
        print(f"   Total Failures: {summary.get('total_failures', 0):,}")
        
        # Performance analysis
        print(f"\n📈 Performance Analysis:")
        
        # Response time analysis
        avg_response = metrics.get('avg_response_time', 0)
        p95_response = metrics.get('p95_response_time', 0)
        p99_response = metrics.get('p99_response_time', 0)
        
        print(f"   Response Times:")
        print(f"     Average: {avg_response:.3f}s")
        print(f"     95th Percentile: {p95_response:.3f}s")
        print(f"     99th Percentile: {p99_response:.3f}s")
        
        # Throughput analysis
        rps = metrics.get('requests_per_second', 0)
        print(f"   Throughput: {rps:.1f} RPS")
        
        # Error analysis
        error_rate = metrics.get('error_rate', 0)
        print(f"   Error Rate: {error_rate:.2%}")
        
        # Performance ratings
        performance_ratings = evaluate_performance(metrics)
        print(f"\n🎯 Performance Ratings:")
        for metric, rating in performance_ratings.items():
            emoji = self._get_rating_emoji(rating)
            print(f"   {metric.replace('_', ' ').title()}: {emoji} {rating.upper()}")
        
        # Acceptance criteria
        print(f"\n✅ Acceptance Criteria:")
        for criterion, passed in validation.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {criterion.replace('_', ' ').title()}: {status}")
        
        overall_pass = result.get('overall_pass', False)
        overall_status = "🎉 PASS" if overall_pass else "❌ FAIL"
        print(f"\n🎯 Overall Result: {overall_status}")
        
        # Recommendations
        self._generate_recommendations(metrics, performance_ratings)
    
    def compare_results(self):
        """Compare multiple test results."""
        if len(self.results) < 2:
            print("⚠️  Need at least 2 results for comparison")
            return
        
        print(f"\n" + "="*80)
        print(f"📊 RESULTS COMPARISON ({len(self.results)} tests)")
        print(f"="*80)
        
        # Sort results by filename (timestamp)
        sorted_results = sorted(self.results, key=lambda x: x.get('filename', ''))
        
        print(f"\n📈 Performance Trends:")
        
        # Extract metrics for comparison
        metrics_data = []
        for result in sorted_results:
            metrics = result.get('performance_metrics', {})
            metrics_data.append({
                'filename': result.get('filename', 'Unknown'),
                'rps': metrics.get('requests_per_second', 0),
                'avg_response': metrics.get('avg_response_time', 0),
                'p95_response': metrics.get('p95_response_time', 0),
                'error_rate': metrics.get('error_rate', 0),
                'users': result.get('test_summary', {}).get('concurrent_users', 0)
            })
        
        # Display comparison table
        print(f"\n{'Test':<25} {'Users':<8} {'RPS':<8} {'Avg RT':<8} {'P95 RT':<8} {'Errors':<8}")
        print(f"{'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
        
        for data in metrics_data:
            filename = data['filename'][:22] + "..." if len(data['filename']) > 25 else data['filename']
            print(f"{filename:<25} {data['users']:<8} {data['rps']:<8.1f} "
                  f"{data['avg_response']:<8.3f} {data['p95_response']:<8.3f} {data['error_rate']:<8.2%}")
        
        # Trend analysis
        if len(metrics_data) >= 2:
            self._analyze_trends(metrics_data)
    
    def _analyze_trends(self, metrics_data: List[Dict[str, Any]]):
        """Analyze performance trends over time."""
        print(f"\n📊 Trend Analysis:")
        
        # Calculate trends
        rps_values = [d['rps'] for d in metrics_data]
        response_values = [d['p95_response'] for d in metrics_data]
        error_values = [d['error_rate'] for d in metrics_data]
        
        # RPS trend
        rps_trend = self._calculate_trend(rps_values)
        rps_emoji = "📈" if rps_trend > 0 else "📉" if rps_trend < 0 else "➡️"
        print(f"   Throughput: {rps_emoji} {rps_trend:+.1f} RPS change")
        
        # Response time trend
        rt_trend = self._calculate_trend(response_values)
        rt_emoji = "📉" if rt_trend < 0 else "📈" if rt_trend > 0 else "➡️"
        print(f"   Response Time: {rt_emoji} {rt_trend:+.3f}s change")
        
        # Error rate trend
        err_trend = self._calculate_trend(error_values)
        err_emoji = "📉" if err_trend < 0 else "📈" if err_trend > 0 else "➡️"
        print(f"   Error Rate: {err_emoji} {err_trend:+.2%} change")
        
        # Overall assessment
        if rps_trend > 0 and rt_trend < 0 and err_trend <= 0:
            print(f"\n🎉 Performance is improving!")
        elif rps_trend < 0 or rt_trend > 0 or err_trend > 0:
            print(f"\n⚠️  Performance may be degrading")
        else:
            print(f"\n➡️  Performance is stable")
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple trend (difference between first and last values)."""
        if len(values) < 2:
            return 0.0
        return values[-1] - values[0]
    
    def _get_rating_emoji(self, rating: str) -> str:
        """Get emoji for performance rating."""
        emoji_map = {
            "excellent": "🟢",
            "good": "🟡",
            "acceptable": "🟠",
            "poor": "🔴"
        }
        return emoji_map.get(rating, "⚪")
    
    def _generate_recommendations(self, metrics: Dict[str, Any], ratings: Dict[str, str]):
        """Generate performance optimization recommendations."""
        print(f"\n💡 Recommendations:")
        
        recommendations = []
        
        # Response time recommendations
        if ratings.get('response_time') in ['acceptable', 'poor']:
            p95_response = metrics.get('p95_response_time', 0)
            if p95_response > 2.0:
                recommendations.append("🔧 Optimize slow endpoints - response times exceed 2s target")
            if p95_response > 1.0:
                recommendations.append("⚡ Consider adding caching layers")
                recommendations.append("🔄 Implement connection pooling")
        
        # Throughput recommendations
        if ratings.get('throughput') in ['acceptable', 'poor']:
            rps = metrics.get('requests_per_second', 0)
            if rps < 100:
                recommendations.append("📈 Scale horizontally - add more server instances")
                recommendations.append("🚀 Increase worker processes/threads")
        
        # Error rate recommendations
        if ratings.get('error_rate') in ['acceptable', 'poor']:
            error_rate = metrics.get('error_rate', 0)
            if error_rate > 0.05:
                recommendations.append("🐛 Investigate and fix high error rates")
                recommendations.append("🔍 Review application logs for error patterns")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ Performance is good - monitor for regressions")
            recommendations.append("📊 Consider running longer endurance tests")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    def generate_report(self, output_file: Optional[str] = None):
        """Generate comprehensive analysis report."""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        report_lines = []
        report_lines.append("# Load Test Analysis Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary statistics
        if len(self.results) > 1:
            report_lines.append("## Summary Statistics")
            
            all_metrics = [r.get('performance_metrics', {}) for r in self.results]
            
            # Calculate averages
            avg_rps = statistics.mean([m.get('requests_per_second', 0) for m in all_metrics])
            avg_response = statistics.mean([m.get('p95_response_time', 0) for m in all_metrics])
            avg_error = statistics.mean([m.get('error_rate', 0) for m in all_metrics])
            
            report_lines.append(f"- Average Throughput: {avg_rps:.1f} RPS")
            report_lines.append(f"- Average P95 Response Time: {avg_response:.3f}s")
            report_lines.append(f"- Average Error Rate: {avg_error:.2%}")
            report_lines.append("")
        
        # Individual test results
        report_lines.append("## Test Results")
        for result in self.results:
            metrics = result.get('performance_metrics', {})
            validation = result.get('validation', {})
            
            report_lines.append(f"### {result.get('filename', 'Unknown')}")
            report_lines.append(f"- Throughput: {metrics.get('requests_per_second', 0):.1f} RPS")
            report_lines.append(f"- P95 Response Time: {metrics.get('p95_response_time', 0):.3f}s")
            report_lines.append(f"- Error Rate: {metrics.get('error_rate', 0):.2%}")
            report_lines.append(f"- Overall Pass: {'✅' if result.get('overall_pass') else '❌'}")
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
            print(f"📄 Report saved to: {output_file}")
        else:
            print(report_content)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze load test results")
    parser.add_argument("--file", help="Specific results file to analyze")
    parser.add_argument("--compare", action="store_true", help="Compare multiple results")
    parser.add_argument("--report", help="Generate report file")
    parser.add_argument("--results-dir", default="results", help="Results directory")
    
    args = parser.parse_args()
    
    analyzer = LoadTestAnalyzer(args.results_dir)
    
    # Load results
    if not analyzer.load_results(args.file):
        sys.exit(1)
    
    # Perform analysis
    if args.compare and len(analyzer.results) > 1:
        analyzer.compare_results()
    else:
        for result in analyzer.results:
            analyzer.analyze_single_result(result)
    
    # Generate report if requested
    if args.report:
        analyzer.generate_report(args.report)


if __name__ == "__main__":
    main()
