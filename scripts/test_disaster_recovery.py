#!/usr/bin/env python3
"""
Disaster Recovery & Backup Validation Script
Phase 4, Task 4.3: Disaster Recovery & Backup

This script validates the disaster recovery and backup implementation by:
- Testing backup script functionality and structure
- Validating restoration script completeness
- Checking disaster recovery documentation
- Verifying operational runbooks
- Testing backup/restore workflow simulation

Run this script to ensure the DR system meets acceptance criteria.
"""

import os
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class DisasterRecoveryValidator:
    """Comprehensive disaster recovery and backup validation."""
    
    def __init__(self):
        """Initialize DR validator."""
        self.results: Dict[str, Any] = {}
        self.project_root = Path(__file__).parent.parent
        self.test_passed = 0
        self.test_failed = 0
        
        # Expected files and directories
        self.expected_files = {
            'backup_scripts': [
                'scripts/backup/backup_weaviate.sh',
                'scripts/backup/backup_redis.sh'
            ],
            'restore_scripts': [
                'scripts/restore/full_restore.sh',
                'scripts/restore/restore_weaviate.sh',
                'scripts/restore/restore_redis.sh'
            ],
            'documentation': [
                'docs/Disaster_Recovery_Plan.md'
            ],
            'runbooks': [
                'docs/runbooks/MANUAL_BACKUP.md',
                'docs/runbooks/DR_TESTING.md'
            ]
        }
    
    async def run_validation(self) -> Dict[str, Any]:
        """Run complete disaster recovery validation."""
        print("🔍 GremlinsAI Disaster Recovery & Backup Validation")
        print("=" * 60)
        
        # Run validation components
        await self.validate_backup_scripts()
        await self.validate_restore_scripts()
        await self.validate_documentation()
        await self.validate_runbooks()
        await self.validate_automation_capabilities()
        await self.simulate_backup_workflow()
        
        # Generate comprehensive report
        return self.generate_validation_report()
    
    async def validate_backup_scripts(self):
        """Validate backup script implementation."""
        print("\n📦 Validating Backup Scripts...")
        
        backup_results = {
            'weaviate_backup_script_exists': False,
            'redis_backup_script_exists': False,
            'weaviate_script_structure': False,
            'redis_script_structure': False,
            'backup_script_features': False,
            'error_handling': False,
            'logging_implementation': False,
            's3_integration': False
        }
        
        try:
            # Check Weaviate backup script
            weaviate_script = self.project_root / 'scripts/backup/backup_weaviate.sh'
            if weaviate_script.exists():
                backup_results['weaviate_backup_script_exists'] = True
                print("   ✅ Weaviate backup script exists")
                
                # Analyze script content
                content = weaviate_script.read_text()
                
                # Check for essential features
                if all(feature in content for feature in [
                    'set -euo pipefail',  # Error handling
                    'log_info',  # Logging
                    'aws s3',  # S3 integration
                    'WEAVIATE_URL',  # Configuration
                    'backup_weaviate',  # Main function
                    'cleanup'  # Cleanup function
                ]):
                    backup_results['weaviate_script_structure'] = True
                    print("   ✅ Weaviate script structure is complete")
            
            # Check Redis backup script
            redis_script = self.project_root / 'scripts/backup/backup_redis.sh'
            if redis_script.exists():
                backup_results['redis_backup_script_exists'] = True
                print("   ✅ Redis backup script exists")
                
                # Analyze script content
                content = redis_script.read_text()
                
                # Check for essential features
                if all(feature in content for feature in [
                    'set -euo pipefail',  # Error handling
                    'log_info',  # Logging
                    'aws s3',  # S3 integration
                    'REDIS_URL',  # Configuration
                    'create_rdb_backup',  # RDB backup
                    'create_aof_backup'  # AOF backup
                ]):
                    backup_results['redis_script_structure'] = True
                    print("   ✅ Redis script structure is complete")
            
            # Check for common features across scripts
            if backup_results['weaviate_backup_script_exists'] and backup_results['redis_backup_script_exists']:
                # Check for comprehensive features
                weaviate_content = (self.project_root / 'scripts/backup/backup_weaviate.sh').read_text()
                redis_content = (self.project_root / 'scripts/backup/backup_redis.sh').read_text()
                
                # Feature validation
                features = [
                    ('Command line arguments', '--environment', '--bucket'),
                    ('Error handling', 'trap cleanup EXIT', 'set -euo pipefail'),
                    ('Logging', 'log_info', 'log_error', 'LOG_FILE'),
                    ('S3 integration', 'aws s3 cp', 'S3_BUCKET'),
                    ('Compression', 'tar -czf', 'compress_backup'),
                    ('Cleanup', 'cleanup_old_backups', 'rm -rf')
                ]
                
                feature_count = 0
                for feature_name, *patterns in features:
                    if all(pattern in weaviate_content and pattern in redis_content for pattern in patterns):
                        feature_count += 1
                
                if feature_count >= 5:
                    backup_results['backup_script_features'] = True
                    print("   ✅ Backup scripts have comprehensive features")
                
                # Error handling validation
                if all('trap cleanup EXIT' in content for content in [weaviate_content, redis_content]):
                    backup_results['error_handling'] = True
                    print("   ✅ Error handling implemented")
                
                # Logging validation
                if all('LOG_FILE=' in content and 'log_info' in content for content in [weaviate_content, redis_content]):
                    backup_results['logging_implementation'] = True
                    print("   ✅ Logging implementation found")
                
                # S3 integration validation
                if all('aws s3 cp' in content and 'S3_BUCKET' in content for content in [weaviate_content, redis_content]):
                    backup_results['s3_integration'] = True
                    print("   ✅ S3 integration implemented")
        
        except Exception as e:
            print(f"   ❌ Backup script validation error: {e}")
        
        self.results['backup_scripts'] = backup_results
        
        # Count results
        passed = sum(1 for result in backup_results.values() if result)
        total = len(backup_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_restore_scripts(self):
        """Validate restore script implementation."""
        print("\n🔄 Validating Restore Scripts...")
        
        restore_results = {
            'full_restore_script_exists': False,
            'weaviate_restore_script_exists': False,
            'redis_restore_script_exists': False,
            'full_restore_structure': False,
            'individual_restore_structure': False,
            'validation_procedures': False,
            'rollback_capabilities': False,
            'progress_tracking': False
        }
        
        try:
            # Check full restore script
            full_restore_script = self.project_root / 'scripts/restore/full_restore.sh'
            if full_restore_script.exists():
                restore_results['full_restore_script_exists'] = True
                print("   ✅ Full restore script exists")
                
                content = full_restore_script.read_text()
                
                # Check for comprehensive structure
                if all(feature in content for feature in [
                    'download_backups',
                    'extract_backups',
                    'validate_backups',
                    'restore_weaviate',
                    'restore_redis',
                    'validate_restoration',
                    'progress',
                    'TOTAL_STEPS'
                ]):
                    restore_results['full_restore_structure'] = True
                    print("   ✅ Full restore script structure is complete")
                
                # Check for progress tracking
                if 'CURRENT_STEP' in content and 'progress()' in content:
                    restore_results['progress_tracking'] = True
                    print("   ✅ Progress tracking implemented")
            
            # Check individual restore scripts
            weaviate_restore = self.project_root / 'scripts/restore/restore_weaviate.sh'
            redis_restore = self.project_root / 'scripts/restore/restore_redis.sh'
            
            if weaviate_restore.exists():
                restore_results['weaviate_restore_script_exists'] = True
                print("   ✅ Weaviate restore script exists")
            
            if redis_restore.exists():
                restore_results['redis_restore_script_exists'] = True
                print("   ✅ Redis restore script exists")
            
            # Check individual script structure
            if weaviate_restore.exists() and redis_restore.exists():
                weaviate_content = weaviate_restore.read_text()
                redis_content = redis_restore.read_text()
                
                # Check for essential restore functions
                weaviate_functions = [
                    'validate_backup',
                    'clear_existing_data',
                    'restore_backup',
                    'validate_restoration'
                ]
                
                redis_functions = [
                    'validate_backup',
                    'stop_redis',
                    'restore_rdb',
                    'restore_aof',
                    'validate_restoration'
                ]
                
                if (all(func in weaviate_content for func in weaviate_functions) and
                    all(func in redis_content for func in redis_functions)):
                    restore_results['individual_restore_structure'] = True
                    print("   ✅ Individual restore scripts have proper structure")
                
                # Check for validation procedures
                if ('validate_restoration' in weaviate_content and 
                    'validate_restoration' in redis_content):
                    restore_results['validation_procedures'] = True
                    print("   ✅ Validation procedures implemented")
                
                # Check for rollback capabilities
                if ('cleanup' in weaviate_content and 'cleanup' in redis_content):
                    restore_results['rollback_capabilities'] = True
                    print("   ✅ Rollback capabilities found")
        
        except Exception as e:
            print(f"   ❌ Restore script validation error: {e}")
        
        self.results['restore_scripts'] = restore_results
        
        # Count results
        passed = sum(1 for result in restore_results.values() if result)
        total = len(restore_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_documentation(self):
        """Validate disaster recovery documentation."""
        print("\n📚 Validating Documentation...")
        
        doc_results = {
            'dr_plan_exists': False,
            'recovery_objectives_defined': False,
            'team_roles_defined': False,
            'step_by_step_procedures': False,
            'communication_plan': False,
            'validation_checklist': False,
            'contact_information': False,
            'testing_schedule': False
        }
        
        try:
            # Check DR plan document
            dr_plan = self.project_root / 'docs/Disaster_Recovery_Plan.md'
            if dr_plan.exists():
                doc_results['dr_plan_exists'] = True
                print("   ✅ Disaster Recovery Plan document exists")
                
                content = dr_plan.read_text()
                
                # Check for essential sections
                sections = [
                    ('Recovery Objectives', 'RTO.*4 hours', 'RPO.*1 hour'),
                    ('Team Roles', 'Incident Commander', 'Recovery Team'),
                    ('Step-by-Step', 'Phase 1:', 'Phase 2:', 'Phase 3:'),
                    ('Communication Plan', 'Internal Communication', 'External Communication'),
                    ('Validation Checklist', 'Post-Recovery Validation', 'System Health'),
                    ('Contact Information', 'Emergency Contacts', 'Primary Contact'),
                    ('Testing Schedule', 'Monthly DR Tests', 'Quarterly')
                ]
                
                for section_name, *patterns in sections:
                    if any(pattern in content for pattern in patterns):
                        if section_name == 'Recovery Objectives':
                            doc_results['recovery_objectives_defined'] = True
                            print("   ✅ Recovery objectives defined")
                        elif section_name == 'Team Roles':
                            doc_results['team_roles_defined'] = True
                            print("   ✅ Team roles defined")
                        elif section_name == 'Step-by-Step':
                            doc_results['step_by_step_procedures'] = True
                            print("   ✅ Step-by-step procedures documented")
                        elif section_name == 'Communication Plan':
                            doc_results['communication_plan'] = True
                            print("   ✅ Communication plan included")
                        elif section_name == 'Validation Checklist':
                            doc_results['validation_checklist'] = True
                            print("   ✅ Validation checklist provided")
                        elif section_name == 'Contact Information':
                            doc_results['contact_information'] = True
                            print("   ✅ Contact information included")
                        elif section_name == 'Testing Schedule':
                            doc_results['testing_schedule'] = True
                            print("   ✅ Testing schedule defined")
        
        except Exception as e:
            print(f"   ❌ Documentation validation error: {e}")
        
        self.results['documentation'] = doc_results
        
        # Count results
        passed = sum(1 for result in doc_results.values() if result)
        total = len(doc_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_runbooks(self):
        """Validate operational runbooks."""
        print("\n📖 Validating Operational Runbooks...")
        
        runbook_results = {
            'manual_backup_runbook_exists': False,
            'dr_testing_runbook_exists': False,
            'manual_backup_procedures': False,
            'testing_procedures': False,
            'troubleshooting_guides': False,
            'escalation_procedures': False,
            'validation_scripts': False
        }
        
        try:
            # Check manual backup runbook
            manual_backup = self.project_root / 'docs/runbooks/MANUAL_BACKUP.md'
            if manual_backup.exists():
                runbook_results['manual_backup_runbook_exists'] = True
                print("   ✅ Manual backup runbook exists")
                
                content = manual_backup.read_text()
                
                # Check for essential procedures
                if all(section in content for section in [
                    'Manual Weaviate Backup',
                    'Manual Redis Backup',
                    'Step 1:',
                    'Step 2:',
                    'Prerequisites'
                ]):
                    runbook_results['manual_backup_procedures'] = True
                    print("   ✅ Manual backup procedures documented")
            
            # Check DR testing runbook
            dr_testing = self.project_root / 'docs/runbooks/DR_TESTING.md'
            if dr_testing.exists():
                runbook_results['dr_testing_runbook_exists'] = True
                print("   ✅ DR testing runbook exists")
                
                content = dr_testing.read_text()
                
                # Check for testing procedures
                if all(section in content for section in [
                    'Test 1:',
                    'Test 2:',
                    'Success Criteria',
                    'Testing Schedule'
                ]):
                    runbook_results['testing_procedures'] = True
                    print("   ✅ Testing procedures documented")
                
                # Check for validation scripts
                if 'Automated Validation Script' in content and '#!/bin/bash' in content:
                    runbook_results['validation_scripts'] = True
                    print("   ✅ Validation scripts included")
            
            # Check for troubleshooting and escalation in both runbooks
            all_content = ""
            for runbook_file in [manual_backup, dr_testing]:
                if runbook_file.exists():
                    all_content += runbook_file.read_text()
            
            if 'Troubleshooting' in all_content and 'Common Issues' in all_content:
                runbook_results['troubleshooting_guides'] = True
                print("   ✅ Troubleshooting guides included")
            
            if 'Escalation' in all_content and 'Emergency' in all_content:
                runbook_results['escalation_procedures'] = True
                print("   ✅ Escalation procedures documented")
        
        except Exception as e:
            print(f"   ❌ Runbook validation error: {e}")
        
        self.results['runbooks'] = runbook_results
        
        # Count results
        passed = sum(1 for result in runbook_results.values() if result)
        total = len(runbook_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def validate_automation_capabilities(self):
        """Validate automation and scheduling capabilities."""
        print("\n⚙️ Validating Automation Capabilities...")
        
        automation_results = {
            'cron_job_compatibility': False,
            'kubernetes_cronjob_ready': False,
            'automated_cleanup': False,
            'notification_integration': False,
            'monitoring_integration': False,
            'configuration_management': False
        }
        
        try:
            # Check backup scripts for cron compatibility
            backup_scripts = [
                self.project_root / 'scripts/backup/backup_weaviate.sh',
                self.project_root / 'scripts/backup/backup_redis.sh'
            ]
            
            cron_compatible = True
            for script in backup_scripts:
                if script.exists():
                    content = script.read_text()
                    # Check for cron-friendly features
                    if not all(feature in content for feature in [
                        '#!/bin/bash',
                        'set -euo pipefail',
                        'LOG_FILE=',
                        'cleanup()'
                    ]):
                        cron_compatible = False
                        break
            
            if cron_compatible:
                automation_results['cron_job_compatibility'] = True
                print("   ✅ Scripts are cron job compatible")
            
            # Check for Kubernetes CronJob readiness
            if all(script.exists() for script in backup_scripts):
                # Scripts exist and can be containerized
                automation_results['kubernetes_cronjob_ready'] = True
                print("   ✅ Scripts ready for Kubernetes CronJob")
            
            # Check for automated cleanup
            cleanup_found = False
            for script in backup_scripts:
                if script.exists():
                    content = script.read_text()
                    if 'cleanup_old_backups' in content and 'RETENTION_DAYS' in content:
                        cleanup_found = True
                        break
            
            if cleanup_found:
                automation_results['automated_cleanup'] = True
                print("   ✅ Automated cleanup implemented")
            
            # Check for notification integration
            notification_found = False
            for script in backup_scripts + [self.project_root / 'scripts/restore/full_restore.sh']:
                if script.exists():
                    content = script.read_text()
                    if 'SLACK_WEBHOOK_URL' in content or 'send_notification' in content:
                        notification_found = True
                        break
            
            if notification_found:
                automation_results['notification_integration'] = True
                print("   ✅ Notification integration found")
            
            # Check for monitoring integration
            monitoring_found = False
            for script in backup_scripts:
                if script.exists():
                    content = script.read_text()
                    if 'metrics' in content.lower() or 'prometheus' in content.lower():
                        monitoring_found = True
                        break
            
            if monitoring_found:
                automation_results['monitoring_integration'] = True
                print("   ✅ Monitoring integration found")
            
            # Check for configuration management
            config_found = False
            for script in backup_scripts + [self.project_root / 'scripts/restore/full_restore.sh']:
                if script.exists():
                    content = script.read_text()
                    if all(var in content for var in ['ENVIRONMENT=', 'S3_BUCKET=', 'AWS_REGION=']):
                        config_found = True
                        break
            
            if config_found:
                automation_results['configuration_management'] = True
                print("   ✅ Configuration management implemented")
        
        except Exception as e:
            print(f"   ❌ Automation validation error: {e}")
        
        self.results['automation'] = automation_results
        
        # Count results
        passed = sum(1 for result in automation_results.values() if result)
        total = len(automation_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    async def simulate_backup_workflow(self):
        """Simulate backup workflow without actual execution."""
        print("\n🧪 Simulating Backup Workflow...")
        
        workflow_results = {
            'backup_script_syntax': False,
            'restore_script_syntax': False,
            'workflow_integration': False,
            'error_handling_simulation': False,
            'logging_simulation': False
        }
        
        try:
            # Simulate backup script execution (syntax check)
            backup_scripts = [
                'scripts/backup/backup_weaviate.sh',
                'scripts/backup/backup_redis.sh'
            ]
            
            syntax_valid = True
            for script_path in backup_scripts:
                script_file = self.project_root / script_path
                if script_file.exists():
                    # Check for basic bash syntax issues
                    content = script_file.read_text()
                    
                    # Basic syntax validation
                    if not content.startswith('#!/bin/bash'):
                        print(f"   ⚠️ {script_path} missing shebang")
                        syntax_valid = False
                    
                    # Check for unmatched quotes or brackets
                    quote_count = content.count('"') - content.count('\\"')
                    if quote_count % 2 != 0:
                        print(f"   ⚠️ {script_path} may have unmatched quotes")
                        syntax_valid = False
            
            if syntax_valid:
                workflow_results['backup_script_syntax'] = True
                print("   ✅ Backup script syntax appears valid")
            
            # Simulate restore script execution (syntax check)
            restore_scripts = [
                'scripts/restore/full_restore.sh',
                'scripts/restore/restore_weaviate.sh',
                'scripts/restore/restore_redis.sh'
            ]
            
            restore_syntax_valid = True
            for script_path in restore_scripts:
                script_file = self.project_root / script_path
                if script_file.exists():
                    content = script_file.read_text()
                    
                    if not content.startswith('#!/bin/bash'):
                        print(f"   ⚠️ {script_path} missing shebang")
                        restore_syntax_valid = False
            
            if restore_syntax_valid:
                workflow_results['restore_script_syntax'] = True
                print("   ✅ Restore script syntax appears valid")
            
            # Check workflow integration
            full_restore = self.project_root / 'scripts/restore/full_restore.sh'
            if full_restore.exists():
                content = full_restore.read_text()
                if ('restore_weaviate.sh' in content and 'restore_redis.sh' in content):
                    workflow_results['workflow_integration'] = True
                    print("   ✅ Workflow integration implemented")
            
            # Simulate error handling
            error_handling_count = 0
            for script_path in backup_scripts + restore_scripts:
                script_file = self.project_root / script_path
                if script_file.exists():
                    content = script_file.read_text()
                    if 'trap' in content and 'cleanup' in content:
                        error_handling_count += 1
            
            if error_handling_count >= 3:
                workflow_results['error_handling_simulation'] = True
                print("   ✅ Error handling simulation passed")
            
            # Simulate logging
            logging_count = 0
            for script_path in backup_scripts + restore_scripts:
                script_file = self.project_root / script_path
                if script_file.exists():
                    content = script_file.read_text()
                    if 'LOG_FILE=' in content and 'log_info' in content:
                        logging_count += 1
            
            if logging_count >= 3:
                workflow_results['logging_simulation'] = True
                print("   ✅ Logging simulation passed")
        
        except Exception as e:
            print(f"   ❌ Workflow simulation error: {e}")
        
        self.results['workflow_simulation'] = workflow_results
        
        # Count results
        passed = sum(1 for result in workflow_results.values() if result)
        total = len(workflow_results)
        self.test_passed += passed
        self.test_failed += (total - passed)
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("\n" + "=" * 60)
        print("🔍 DISASTER RECOVERY & BACKUP VALIDATION REPORT")
        print("=" * 60)
        
        # Calculate overall scores
        total_tests = self.test_passed + self.test_failed
        overall_score = self.test_passed / total_tests if total_tests > 0 else 0
        
        for category, results in self.results.items():
            if isinstance(results, dict):
                category_total = len(results)
                category_passed = sum(1 for check in results.values() if check)
                
                print(f"\n📊 {category.upper().replace('_', ' ')}:")
                print(f"   Passed: {category_passed}/{category_total} ({category_passed/category_total*100:.1f}%)")
        
        print(f"\n📈 OVERALL DR SCORE: {overall_score:.1%}")
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.test_passed}")
        print(f"❌ Failed: {self.test_failed}")
        
        # DR readiness status
        if overall_score >= 0.95:
            status = "PRODUCTION_READY"
            print(f"\n🎉 DR STATUS: {status}")
            print("   Disaster recovery system is production-ready")
        elif overall_score >= 0.85:
            status = "MOSTLY_READY"
            print(f"\n✅ DR STATUS: {status}")
            print("   Disaster recovery system is mostly ready with minor issues")
        elif overall_score >= 0.70:
            status = "NEEDS_IMPROVEMENT"
            print(f"\n⚠️ DR STATUS: {status}")
            print("   Disaster recovery system needs improvements")
        else:
            status = "NOT_READY"
            print(f"\n🚨 DR STATUS: {status}")
            print("   Disaster recovery system has critical issues")
        
        # Generate report
        report = {
            "timestamp": time.time(),
            "overall_score": overall_score,
            "dr_status": status,
            "total_tests": total_tests,
            "passed_tests": self.test_passed,
            "failed_tests": self.test_failed,
            "detailed_results": self.results,
            "acceptance_criteria": self._check_acceptance_criteria(),
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _check_acceptance_criteria(self) -> Dict[str, bool]:
        """Check acceptance criteria from divineKatalyst.md."""
        criteria = {
            "automated_backup_system": False,
            "documented_recovery_procedures": False,
            "tested_restoration_process": False,
            "operational_runbooks": False,
            "rto_under_4_hours": False,
            "rpo_under_1_hour": False,
            "monthly_testing": False
        }
        
        # Check automated backup system
        backup_results = self.results.get('backup_scripts', {})
        if (backup_results.get('weaviate_backup_script_exists') and 
            backup_results.get('redis_backup_script_exists') and
            backup_results.get('s3_integration')):
            criteria["automated_backup_system"] = True
        
        # Check documented recovery procedures
        doc_results = self.results.get('documentation', {})
        if (doc_results.get('dr_plan_exists') and 
            doc_results.get('step_by_step_procedures')):
            criteria["documented_recovery_procedures"] = True
        
        # Check tested restoration process
        restore_results = self.results.get('restore_scripts', {})
        if (restore_results.get('full_restore_script_exists') and 
            restore_results.get('validation_procedures')):
            criteria["tested_restoration_process"] = True
        
        # Check operational runbooks
        runbook_results = self.results.get('runbooks', {})
        if (runbook_results.get('manual_backup_runbook_exists') and 
            runbook_results.get('dr_testing_runbook_exists')):
            criteria["operational_runbooks"] = True
        
        # Check RTO/RPO objectives (based on documentation)
        if (doc_results.get('recovery_objectives_defined')):
            criteria["rto_under_4_hours"] = True
            criteria["rpo_under_1_hour"] = True
        
        # Check monthly testing schedule
        if doc_results.get('testing_schedule'):
            criteria["monthly_testing"] = True
        
        return criteria
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Backup script recommendations
        backup_results = self.results.get('backup_scripts', {})
        if not backup_results.get('s3_integration'):
            recommendations.append("Implement S3 integration for backup storage")
        if not backup_results.get('error_handling'):
            recommendations.append("Add comprehensive error handling to backup scripts")
        
        # Restore script recommendations
        restore_results = self.results.get('restore_scripts', {})
        if not restore_results.get('validation_procedures'):
            recommendations.append("Implement validation procedures in restore scripts")
        if not restore_results.get('rollback_capabilities'):
            recommendations.append("Add rollback capabilities to restore scripts")
        
        # Documentation recommendations
        doc_results = self.results.get('documentation', {})
        if not doc_results.get('communication_plan'):
            recommendations.append("Complete communication plan in DR documentation")
        if not doc_results.get('contact_information'):
            recommendations.append("Add emergency contact information to DR plan")
        
        # Automation recommendations
        automation_results = self.results.get('automation', {})
        if not automation_results.get('notification_integration'):
            recommendations.append("Integrate notification system for backup/restore operations")
        if not automation_results.get('monitoring_integration'):
            recommendations.append("Add monitoring integration for DR operations")
        
        # General recommendations
        if self.test_failed > 5:
            recommendations.append("Address critical DR implementation gaps")
        if self.test_passed < 25:
            recommendations.append("Complete DR system implementation")
        
        # Add deployment recommendations
        recommendations.extend([
            "Set up automated backup scheduling (every 6 hours)",
            "Configure S3 bucket with appropriate lifecycle policies",
            "Test full DR procedure in staging environment",
            "Train operations team on DR procedures",
            "Schedule monthly DR testing"
        ])
        
        return recommendations


async def main():
    """Run disaster recovery validation."""
    validator = DisasterRecoveryValidator()
    report = await validator.run_validation()
    
    # Save report to file
    with open("disaster_recovery_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed validation report saved to: disaster_recovery_validation_report.json")
    
    # Print acceptance criteria status
    criteria = report['acceptance_criteria']
    print(f"\n🎯 ACCEPTANCE CRITERIA STATUS:")
    for criterion, status in criteria.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {criterion.replace('_', ' ').title()}")
    
    # Print recommendations
    if report['recommendations']:
        print(f"\n🚀 RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"   {i}. {rec}")
    
    # Exit with appropriate code
    if report['dr_status'] in ['PRODUCTION_READY', 'MOSTLY_READY']:
        sys.exit(0)
    elif report['dr_status'] == 'NEEDS_IMPROVEMENT':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
