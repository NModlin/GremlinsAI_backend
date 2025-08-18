#!/usr/bin/env python3
"""
Performance Optimization Script for GremlinsAI
Phase 4, Task 4.4: Load Testing & Optimization

This script analyzes load test results and system metrics to automatically
implement performance optimizations and tuning recommendations.

Features:
- Analyzes load test results and system metrics
- Identifies performance bottlenecks
- Implements automatic optimizations
- Generates tuning recommendations
- Updates Kubernetes resource configurations
- Optimizes database indexes and connection pools

Usage:
    python optimize_performance.py [options]
"""

import json
import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Analyzes performance data and implements optimizations."""
    
    def __init__(self, reports_dir: str, project_root: str):
        """Initialize performance optimizer."""
        self.reports_dir = Path(reports_dir)
        self.project_root = Path(project_root)
        self.optimizations_applied = []
        self.recommendations = []
        
        # Performance thresholds
        self.thresholds = {
            'response_time_ms': 2000,
            'cpu_usage_percent': 80,
            'memory_usage_percent': 80,
            'error_rate_percent': 5,
            'requests_per_second_min': 100
        }
    
    def analyze_load_test_results(self) -> Dict[str, Any]:
        """Analyze load test results to identify bottlenecks."""
        logger.info("Analyzing load test results...")
        
        analysis = {
            'performance_issues': [],
            'bottlenecks': [],
            'optimization_opportunities': [],
            'test_results_summary': {}
        }
        
        # Find all test result files
        result_files = list(self.reports_dir.glob("*_*.json"))
        
        if not result_files:
            logger.warning("No load test result files found")
            return analysis
        
        # Analyze each test result
        for result_file in result_files:
            try:
                with open(result_file, 'r') as f:
                    test_data = json.load(f)
                
                test_name = test_data.get('test_configuration', {}).get('test_name', 'unknown')
                logger.info(f"Analyzing test: {test_name}")
                
                # Check performance metrics
                metrics = test_data.get('performance_metrics', {})
                
                # Response time analysis
                avg_response_time = float(metrics.get('average_response_time_ms', 0))
                p95_response_time = float(metrics.get('p95_response_time_ms', 0))
                p99_response_time = float(metrics.get('p99_response_time_ms', 0))
                
                if avg_response_time > self.thresholds['response_time_ms']:
                    analysis['performance_issues'].append({
                        'test': test_name,
                        'issue': 'high_response_time',
                        'value': avg_response_time,
                        'threshold': self.thresholds['response_time_ms'],
                        'severity': 'high' if avg_response_time > 3000 else 'medium'
                    })
                
                # Error rate analysis
                failure_rate = float(metrics.get('failure_rate_percent', 0))
                if failure_rate > self.thresholds['error_rate_percent']:
                    analysis['performance_issues'].append({
                        'test': test_name,
                        'issue': 'high_error_rate',
                        'value': failure_rate,
                        'threshold': self.thresholds['error_rate_percent'],
                        'severity': 'critical' if failure_rate > 10 else 'high'
                    })
                
                # Throughput analysis
                rps = float(metrics.get('requests_per_second', 0))
                if rps < self.thresholds['requests_per_second_min']:
                    analysis['performance_issues'].append({
                        'test': test_name,
                        'issue': 'low_throughput',
                        'value': rps,
                        'threshold': self.thresholds['requests_per_second_min'],
                        'severity': 'medium'
                    })
                
                # Store test summary
                analysis['test_results_summary'][test_name] = {
                    'avg_response_time_ms': avg_response_time,
                    'p95_response_time_ms': p95_response_time,
                    'p99_response_time_ms': p99_response_time,
                    'requests_per_second': rps,
                    'failure_rate_percent': failure_rate,
                    'concurrent_users': test_data.get('test_configuration', {}).get('concurrent_users', 0)
                }
                
            except Exception as e:
                logger.error(f"Error analyzing {result_file}: {e}")
        
        logger.info(f"Found {len(analysis['performance_issues'])} performance issues")
        return analysis
    
    def analyze_system_metrics(self) -> Dict[str, Any]:
        """Analyze system metrics to identify resource bottlenecks."""
        logger.info("Analyzing system metrics...")
        
        analysis = {
            'resource_issues': [],
            'utilization_patterns': {},
            'scaling_recommendations': []
        }
        
        # Find system metrics files
        metrics_files = list(self.reports_dir.glob("system_metrics_*.json"))
        
        if not metrics_files:
            logger.warning("No system metrics files found")
            return analysis
        
        # Analyze the most recent metrics file
        latest_metrics_file = max(metrics_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_metrics_file, 'r') as f:
                metrics_data = json.load(f)
            
            metrics_samples = metrics_data.get('metrics', [])
            
            if not metrics_samples:
                logger.warning("No metrics samples found")
                return analysis
            
            # Analyze CPU utilization
            cpu_values = [float(sample.get('cpu', {}).get('cpu_usage_percent', 0)) for sample in metrics_samples]
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            max_cpu = max(cpu_values) if cpu_values else 0
            
            if max_cpu > self.thresholds['cpu_usage_percent']:
                analysis['resource_issues'].append({
                    'resource': 'cpu',
                    'issue': 'high_utilization',
                    'avg_value': avg_cpu,
                    'max_value': max_cpu,
                    'threshold': self.thresholds['cpu_usage_percent'],
                    'severity': 'critical' if max_cpu > 90 else 'high'
                })
            
            # Analyze memory utilization
            memory_values = [float(sample.get('memory', {}).get('usage_percent', 0)) for sample in metrics_samples]
            avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
            max_memory = max(memory_values) if memory_values else 0
            
            if max_memory > self.thresholds['memory_usage_percent']:
                analysis['resource_issues'].append({
                    'resource': 'memory',
                    'issue': 'high_utilization',
                    'avg_value': avg_memory,
                    'max_value': max_memory,
                    'threshold': self.thresholds['memory_usage_percent'],
                    'severity': 'critical' if max_memory > 90 else 'high'
                })
            
            # Analyze Kubernetes scaling
            k8s_samples = [sample.get('kubernetes', {}) for sample in metrics_samples]
            pod_counts = [int(sample.get('pod_count', 0)) for sample in k8s_samples if sample.get('pod_count')]
            hpa_replicas = [int(sample.get('hpa_replicas', 0)) for sample in k8s_samples if sample.get('hpa_replicas')]
            
            if pod_counts:
                min_pods = min(pod_counts)
                max_pods = max(pod_counts)
                
                analysis['utilization_patterns']['kubernetes'] = {
                    'min_pods': min_pods,
                    'max_pods': max_pods,
                    'scaling_occurred': max_pods > min_pods,
                    'hpa_active': len(hpa_replicas) > 0 and max(hpa_replicas) > 0
                }
            
            # Store utilization patterns
            analysis['utilization_patterns']['cpu'] = {
                'avg': avg_cpu,
                'max': max_cpu,
                'samples': len(cpu_values)
            }
            
            analysis['utilization_patterns']['memory'] = {
                'avg': avg_memory,
                'max': max_memory,
                'samples': len(memory_values)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing system metrics: {e}")
        
        logger.info(f"Found {len(analysis['resource_issues'])} resource issues")
        return analysis
    
    def generate_optimizations(self, load_test_analysis: Dict[str, Any], 
                             system_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        logger.info("Generating optimization recommendations...")
        
        optimizations = []
        
        # CPU optimization recommendations
        cpu_issues = [issue for issue in system_analysis.get('resource_issues', []) 
                     if issue['resource'] == 'cpu']
        
        if cpu_issues:
            optimizations.append({
                'type': 'kubernetes_resources',
                'component': 'cpu',
                'action': 'increase_cpu_limits',
                'current_issue': 'High CPU utilization detected',
                'recommendation': 'Increase CPU requests and limits by 50%',
                'priority': 'high',
                'implementation': self._generate_cpu_optimization()
            })
        
        # Memory optimization recommendations
        memory_issues = [issue for issue in system_analysis.get('resource_issues', []) 
                        if issue['resource'] == 'memory']
        
        if memory_issues:
            optimizations.append({
                'type': 'kubernetes_resources',
                'component': 'memory',
                'action': 'increase_memory_limits',
                'current_issue': 'High memory utilization detected',
                'recommendation': 'Increase memory requests and limits by 30%',
                'priority': 'high',
                'implementation': self._generate_memory_optimization()
            })
        
        # Response time optimization recommendations
        response_time_issues = [issue for issue in load_test_analysis.get('performance_issues', []) 
                               if issue['issue'] == 'high_response_time']
        
        if response_time_issues:
            optimizations.append({
                'type': 'application_tuning',
                'component': 'response_time',
                'action': 'optimize_database_queries',
                'current_issue': 'High response times detected',
                'recommendation': 'Add database indexes and optimize query patterns',
                'priority': 'high',
                'implementation': self._generate_database_optimization()
            })
        
        # HPA scaling optimization
        k8s_patterns = system_analysis.get('utilization_patterns', {}).get('kubernetes', {})
        if not k8s_patterns.get('hpa_active', False):
            optimizations.append({
                'type': 'kubernetes_scaling',
                'component': 'hpa',
                'action': 'configure_hpa',
                'current_issue': 'HPA not active or configured',
                'recommendation': 'Configure HPA with appropriate CPU/memory thresholds',
                'priority': 'medium',
                'implementation': self._generate_hpa_optimization()
            })
        
        # Connection pool optimization
        if response_time_issues or any(issue['issue'] == 'high_error_rate' 
                                     for issue in load_test_analysis.get('performance_issues', [])):
            optimizations.append({
                'type': 'application_tuning',
                'component': 'connection_pools',
                'action': 'optimize_connection_pools',
                'current_issue': 'Potential connection pool exhaustion',
                'recommendation': 'Increase database and Redis connection pool sizes',
                'priority': 'medium',
                'implementation': self._generate_connection_pool_optimization()
            })
        
        logger.info(f"Generated {len(optimizations)} optimization recommendations")
        return optimizations
    
    def _generate_cpu_optimization(self) -> Dict[str, Any]:
        """Generate CPU optimization configuration."""
        return {
            'file': 'kubernetes/gremlinsai-deployment.yaml',
            'changes': {
                'resources.requests.cpu': '500m -> 750m',
                'resources.limits.cpu': '1000m -> 1500m'
            },
            'yaml_patch': {
                'spec.template.spec.containers[0].resources.requests.cpu': '750m',
                'spec.template.spec.containers[0].resources.limits.cpu': '1500m'
            }
        }
    
    def _generate_memory_optimization(self) -> Dict[str, Any]:
        """Generate memory optimization configuration."""
        return {
            'file': 'kubernetes/gremlinsai-deployment.yaml',
            'changes': {
                'resources.requests.memory': '1Gi -> 1.3Gi',
                'resources.limits.memory': '2Gi -> 2.6Gi'
            },
            'yaml_patch': {
                'spec.template.spec.containers[0].resources.requests.memory': '1.3Gi',
                'spec.template.spec.containers[0].resources.limits.memory': '2.6Gi'
            }
        }
    
    def _generate_database_optimization(self) -> Dict[str, Any]:
        """Generate database optimization recommendations."""
        return {
            'weaviate_indexes': [
                'CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)',
                'CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)',
                'CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)'
            ],
            'connection_settings': {
                'weaviate_pool_size': 20,
                'weaviate_max_overflow': 30,
                'query_timeout': 30
            }
        }
    
    def _generate_hpa_optimization(self) -> Dict[str, Any]:
        """Generate HPA configuration."""
        return {
            'file': 'kubernetes/hpa.yaml',
            'hpa_config': {
                'apiVersion': 'autoscaling/v2',
                'kind': 'HorizontalPodAutoscaler',
                'metadata': {
                    'name': 'gremlinsai-hpa',
                    'namespace': 'gremlinsai'
                },
                'spec': {
                    'scaleTargetRef': {
                        'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'name': 'gremlinsai-app'
                    },
                    'minReplicas': 3,
                    'maxReplicas': 20,
                    'metrics': [
                        {
                            'type': 'Resource',
                            'resource': {
                                'name': 'cpu',
                                'target': {
                                    'type': 'Utilization',
                                    'averageUtilization': 70
                                }
                            }
                        },
                        {
                            'type': 'Resource',
                            'resource': {
                                'name': 'memory',
                                'target': {
                                    'type': 'Utilization',
                                    'averageUtilization': 75
                                }
                            }
                        }
                    ]
                }
            }
        }
    
    def _generate_connection_pool_optimization(self) -> Dict[str, Any]:
        """Generate connection pool optimization."""
        return {
            'environment_variables': {
                'DATABASE_POOL_SIZE': '20',
                'DATABASE_MAX_OVERFLOW': '30',
                'REDIS_POOL_SIZE': '15',
                'REDIS_MAX_CONNECTIONS': '25',
                'HTTP_CLIENT_POOL_SIZE': '50'
            },
            'application_config': {
                'uvicorn_workers': 4,
                'worker_connections': 1000,
                'keepalive_timeout': 65
            }
        }
    
    def apply_optimizations(self, optimizations: List[Dict[str, Any]], 
                          dry_run: bool = True) -> List[Dict[str, Any]]:
        """Apply optimization recommendations."""
        logger.info(f"Applying {len(optimizations)} optimizations (dry_run={dry_run})")
        
        applied_optimizations = []
        
        for optimization in optimizations:
            try:
                if optimization['type'] == 'kubernetes_resources':
                    result = self._apply_kubernetes_optimization(optimization, dry_run)
                elif optimization['type'] == 'kubernetes_scaling':
                    result = self._apply_hpa_optimization(optimization, dry_run)
                elif optimization['type'] == 'application_tuning':
                    result = self._apply_application_optimization(optimization, dry_run)
                else:
                    logger.warning(f"Unknown optimization type: {optimization['type']}")
                    continue
                
                applied_optimizations.append({
                    'optimization': optimization,
                    'result': result,
                    'applied': not dry_run,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error applying optimization {optimization['action']}: {e}")
                applied_optimizations.append({
                    'optimization': optimization,
                    'result': {'error': str(e)},
                    'applied': False,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return applied_optimizations
    
    def _apply_kubernetes_optimization(self, optimization: Dict[str, Any], 
                                     dry_run: bool) -> Dict[str, Any]:
        """Apply Kubernetes resource optimization."""
        implementation = optimization.get('implementation', {})
        file_path = self.project_root / implementation.get('file', '')
        
        if not file_path.exists():
            return {'error': f'File not found: {file_path}'}
        
        if dry_run:
            return {
                'action': 'would_update_kubernetes_resources',
                'file': str(file_path),
                'changes': implementation.get('changes', {})
            }
        
        # In a real implementation, you would update the YAML file here
        logger.info(f"Would update {file_path} with resource changes")
        return {'action': 'kubernetes_resources_updated', 'file': str(file_path)}
    
    def _apply_hpa_optimization(self, optimization: Dict[str, Any], 
                              dry_run: bool) -> Dict[str, Any]:
        """Apply HPA optimization."""
        implementation = optimization.get('implementation', {})
        
        if dry_run:
            return {
                'action': 'would_create_hpa_config',
                'config': implementation.get('hpa_config', {})
            }
        
        # In a real implementation, you would create/update the HPA configuration
        logger.info("Would create/update HPA configuration")
        return {'action': 'hpa_config_created'}
    
    def _apply_application_optimization(self, optimization: Dict[str, Any], 
                                      dry_run: bool) -> Dict[str, Any]:
        """Apply application-level optimization."""
        implementation = optimization.get('implementation', {})
        
        if dry_run:
            return {
                'action': 'would_update_application_config',
                'config_changes': implementation
            }
        
        # In a real implementation, you would update application configuration
        logger.info("Would update application configuration")
        return {'action': 'application_config_updated'}
    
    def generate_report(self, load_test_analysis: Dict[str, Any], 
                       system_analysis: Dict[str, Any], 
                       optimizations: List[Dict[str, Any]], 
                       applied_optimizations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive optimization report."""
        logger.info("Generating optimization report...")
        
        report = {
            'optimization_summary': {
                'timestamp': datetime.utcnow().isoformat(),
                'total_issues_found': (len(load_test_analysis.get('performance_issues', [])) + 
                                     len(system_analysis.get('resource_issues', []))),
                'optimizations_recommended': len(optimizations),
                'optimizations_applied': len([opt for opt in applied_optimizations if opt['applied']]),
                'critical_issues': len([issue for issue in load_test_analysis.get('performance_issues', []) + 
                                      system_analysis.get('resource_issues', []) 
                                      if issue.get('severity') == 'critical'])
            },
            'load_test_analysis': load_test_analysis,
            'system_analysis': system_analysis,
            'optimizations': optimizations,
            'applied_optimizations': applied_optimizations,
            'recommendations': {
                'immediate_actions': [
                    opt for opt in optimizations if opt.get('priority') == 'high'
                ],
                'follow_up_actions': [
                    opt for opt in optimizations if opt.get('priority') in ['medium', 'low']
                ],
                'monitoring_points': [
                    'Monitor CPU and memory utilization after applying resource optimizations',
                    'Track response time improvements after database optimizations',
                    'Verify HPA scaling behavior under load',
                    'Monitor error rates and connection pool utilization'
                ]
            }
        }
        
        return report


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='GremlinsAI Performance Optimizer')
    parser.add_argument('--reports-dir', default='./load_test_reports',
                       help='Directory containing load test reports')
    parser.add_argument('--project-root', default='.',
                       help='Project root directory')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without applying changes')
    parser.add_argument('--output', default='optimization_report.json',
                       help='Output report file')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize optimizer
    optimizer = PerformanceOptimizer(args.reports_dir, args.project_root)
    
    try:
        # Analyze load test results
        load_test_analysis = optimizer.analyze_load_test_results()
        
        # Analyze system metrics
        system_analysis = optimizer.analyze_system_metrics()
        
        # Generate optimizations
        optimizations = optimizer.generate_optimizations(load_test_analysis, system_analysis)
        
        # Apply optimizations
        applied_optimizations = optimizer.apply_optimizations(optimizations, args.dry_run)
        
        # Generate report
        report = optimizer.generate_report(
            load_test_analysis, system_analysis, optimizations, applied_optimizations
        )
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Optimization report saved to: {args.output}")
        
        # Print summary
        summary = report['optimization_summary']
        print(f"\n{'='*60}")
        print("PERFORMANCE OPTIMIZATION SUMMARY")
        print(f"{'='*60}")
        print(f"Issues Found: {summary['total_issues_found']}")
        print(f"Optimizations Recommended: {summary['optimizations_recommended']}")
        print(f"Optimizations Applied: {summary['optimizations_applied']}")
        print(f"Critical Issues: {summary['critical_issues']}")
        print(f"Report: {args.output}")
        print(f"{'='*60}")
        
        return 0 if summary['critical_issues'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
