# tests/utils/logging_utils.py
"""
Test Logging Utilities

Provides comprehensive logging functionality for test executions including
timestamped log files, output capture, log rotation, and tee functionality.
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, IO, Any
from contextlib import contextmanager
import glob
import threading
import queue


class TeeOutput:
    """
    Tee-like functionality to write output to both console and file simultaneously.
    Thread-safe implementation for capturing subprocess output.
    """
    
    def __init__(self, file_handle: IO[str], console_handle: IO[str]):
        self.file_handle = file_handle
        self.console_handle = console_handle
        self.lock = threading.Lock()
    
    def write(self, data: str) -> None:
        """Write data to both file and console."""
        with self.lock:
            self.file_handle.write(data)
            self.file_handle.flush()
            self.console_handle.write(data)
            self.console_handle.flush()
    
    def flush(self) -> None:
        """Flush both file and console handles."""
        with self.lock:
            self.file_handle.flush()
            self.console_handle.flush()


class TestLogger:
    """
    Comprehensive test logging system with timestamped files, rotation, and tee functionality.
    """
    
    def __init__(self, logs_dir: str = "tests/logs", max_log_files: int = 10):
        self.logs_dir = Path(logs_dir)
        self.max_log_files = max_log_files
        self.current_log_file: Optional[Path] = None
        self.log_handle: Optional[IO[str]] = None
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger("test_runner")
        self.logger.setLevel(logging.DEBUG)
    
    def create_log_file(self, test_category: str = "general") -> Path:
        """Create a new timestamped log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"test_run_{test_category}_{timestamp}.log"
        log_path = self.logs_dir / log_filename
        
        self.current_log_file = log_path
        return log_path
    
    def rotate_logs(self) -> None:
        """Remove old log files, keeping only the most recent max_log_files."""
        log_files = list(self.logs_dir.glob("test_run_*.log"))
        
        if len(log_files) > self.max_log_files:
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove oldest files
            files_to_remove = log_files[self.max_log_files:]
            for old_file in files_to_remove:
                try:
                    old_file.unlink()
                    print(f"Removed old log file: {old_file.name}")
                except OSError as e:
                    print(f"Warning: Could not remove old log file {old_file.name}: {e}")
    
    def get_log_header(self, test_category: str, command: str) -> str:
        """Generate a comprehensive log header."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80
        
        header = f"""
{separator}
GREMLINSAI BACKEND TEST EXECUTION LOG
{separator}
Timestamp: {timestamp}
Test Category: {test_category}
Command: {command}
Python Version: {sys.version}
Working Directory: {os.getcwd()}
Log File: {self.current_log_file}
{separator}

"""
        return header
    
    def get_log_footer(self, duration: float, return_code: int) -> str:
        """Generate a comprehensive log footer."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80
        
        status = "SUCCESS" if return_code == 0 else "FAILED"
        
        footer = f"""

{separator}
TEST EXECUTION COMPLETED
{separator}
End Timestamp: {timestamp}
Duration: {duration:.2f} seconds
Exit Code: {return_code}
Status: {status}
{separator}
"""
        return footer
    
    @contextmanager
    def capture_output(self, test_category: str, command: str):
        """
        Context manager for capturing all output to both console and log file.
        """
        log_file = self.create_log_file(test_category)
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                # Write log header
                header = self.get_log_header(test_category, command)
                f.write(header)
                f.flush()
                
                # Print header to console as well
                print(header.strip())
                
                # Create tee output for both stdout and stderr
                stdout_tee = TeeOutput(f, sys.stdout)
                stderr_tee = TeeOutput(f, sys.stderr)
                
                yield {
                    'log_file': log_file,
                    'stdout_tee': stdout_tee,
                    'stderr_tee': stderr_tee,
                    'file_handle': f
                }
                
        except Exception as e:
            print(f"Error setting up logging: {e}")
            # Fallback to no logging
            yield {
                'log_file': None,
                'stdout_tee': sys.stdout,
                'stderr_tee': sys.stderr,
                'file_handle': None
            }
        
        finally:
            # Rotate logs after execution
            self.rotate_logs()
    
    def run_command_with_logging(self, command: List[str], test_category: str, 
                                cwd: Optional[str] = None) -> dict:
        """
        Run a command with comprehensive logging to both console and file.
        """
        command_str = " ".join(command)
        start_time = datetime.now()
        
        with self.capture_output(test_category, command_str) as capture:
            log_file = capture['log_file']
            file_handle = capture['file_handle']
            
            try:
                # Run the command with real-time output capture
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout
                    text=True,
                    bufsize=1,  # Line buffered
                    universal_newlines=True,
                    cwd=cwd
                )
                
                # Real-time output processing
                output_lines = []
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output_lines.append(output.rstrip())
                        # Write to both console and file
                        print(output.rstrip())
                        if file_handle:
                            file_handle.write(output)
                            file_handle.flush()
                
                # Wait for process to complete
                return_code = process.poll()
                
                # Calculate duration
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Write footer to log file
                if file_handle:
                    footer = self.get_log_footer(duration, return_code)
                    file_handle.write(footer)
                    file_handle.flush()
                
                # Print summary to console
                status = "SUCCESS" if return_code == 0 else "FAILED"
                summary = f"\n{'='*50}\nTest execution completed: {status}\nDuration: {duration:.2f}s\nLog saved to: {log_file}\n{'='*50}"
                print(summary)
                
                return {
                    'success': return_code == 0,
                    'return_code': return_code,
                    'duration': duration,
                    'command': command_str,
                    'log_file': str(log_file) if log_file else None,
                    'output_lines': output_lines
                }
                
            except Exception as e:
                error_msg = f"Error executing command: {e}"
                print(error_msg)
                if file_handle:
                    file_handle.write(f"\nERROR: {error_msg}\n")
                    file_handle.flush()
                
                return {
                    'success': False,
                    'return_code': -1,
                    'duration': 0,
                    'command': command_str,
                    'error': str(e),
                    'log_file': str(log_file) if log_file else None,
                    'output_lines': []
                }
    
    def list_recent_logs(self, count: int = 5) -> List[Path]:
        """List the most recent log files."""
        log_files = list(self.logs_dir.glob("test_run_*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return log_files[:count]
    
    def get_log_summary(self) -> dict:
        """Get a summary of available log files."""
        log_files = list(self.logs_dir.glob("test_run_*.log"))
        
        if not log_files:
            return {
                'total_logs': 0,
                'logs_directory': str(self.logs_dir),
                'recent_logs': []
            }
        
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        recent_logs = []
        for log_file in log_files[:5]:
            stat = log_file.stat()
            recent_logs.append({
                'filename': log_file.name,
                'path': str(log_file),
                'size_kb': round(stat.st_size / 1024, 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            'total_logs': len(log_files),
            'logs_directory': str(self.logs_dir),
            'recent_logs': recent_logs
        }


def get_test_category_from_args(args: List[str]) -> str:
    """Extract test category from command arguments."""
    if '-m' in args:
        marker_index = args.index('-m') + 1
        if marker_index < len(args):
            marker = args[marker_index]
            if 'unit' in marker:
                return 'unit'
            elif 'integration' in marker:
                return 'integration'
            elif 'e2e' in marker:
                return 'e2e'
            elif 'performance' in marker:
                return 'performance'
    
    # Check for directory-based categorization
    for arg in args:
        if 'unit' in arg:
            return 'unit'
        elif 'integration' in arg:
            return 'integration'
        elif 'e2e' in arg:
            return 'e2e'
        elif 'performance' in arg:
            return 'performance'
    
    return 'general'
