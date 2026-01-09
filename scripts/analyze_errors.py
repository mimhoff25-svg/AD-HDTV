#!/usr/bin/env python3
"""
AD-HDTV Error Analysis Tool

This script analyzes error logs to identify patterns and provide insights.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import argparse


class ErrorAnalyzer:
    """Analyze AD-HDTV error logs."""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.error_patterns = {
            'vlc_errors': [
                r'vlc.*failed',
                r'player error #\d+',
                r'media player.*failed',
                r'vlc instance.*failed'
            ],
            'network_errors': [
                r'connection.*timeout',
                r'requests.*timeout',
                r'stream.*unavailable',
                r'http.*error'
            ],
            'audio_errors': [
                r'audio.*glitch',
                r'volume.*pop',
                r'audio.*distorted',
                r'crackling'
            ],
            'ui_errors': [
                r'css.*warning',
                r'box-shadow',
                r'widget.*error',
                r'qt.*error'
            ],
            'file_errors': [
                r'permission denied',
                r'file.*not found',
                r'directory.*error',
                r'cannot write'
            ]
        }
    
    def get_recent_logs(self, days: int = 7) -> List[Path]:
        """Get log files from the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        log_files = []
        
        for pattern in ['ad-hdtv_*.log', 'errors_*.log', 'known_errors_*.log']:
            for log_file in self.logs_dir.glob(pattern):
                try:
                    # Extract date from filename
                    date_str = log_file.stem.split('_')[-1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    if file_date >= cutoff_date:
                        log_files.append(log_file)
                except ValueError:
                    # Skip files with unexpected naming
                    continue
        
        return sorted(log_files)
    
    def analyze_error_patterns(self, log_files: List[Path]) -> Dict:
        """Analyze error patterns across log files."""
        pattern_counts = defaultdict(int)
        error_timeline = defaultdict(list)
        severity_counts = Counter()
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract date from filename for timeline
                date_str = log_file.stem.split('_')[-1]
                
                # Count pattern occurrences
                for category, patterns in self.error_patterns.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            pattern_counts[category] += len(matches)
                            error_timeline[date_str].append(f"{category}: {len(matches)}")
                
                # Extract severity information
                severity_matches = re.findall(r'Severity: (\w+)', content)
                for severity in severity_matches:
                    severity_counts[severity] += 1
            
            except Exception as e:
                print(f"Warning: Could not analyze {log_file}: {e}")
        
        return {
            'pattern_counts': dict(pattern_counts),
            'error_timeline': dict(error_timeline),
            'severity_counts': dict(severity_counts)
        }
    
    def find_recurring_errors(self, log_files: List[Path], min_occurrences: int = 3) -> List[Dict]:
        """Find errors that occur repeatedly."""
        error_messages = []
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'ERROR' in line.upper():
                            # Extract the actual error message
                            error_msg = line.strip()
                            error_messages.append(error_msg)
            except Exception as e:
                print(f"Warning: Could not read {log_file}: {e}")
        
        # Count occurrences
        error_counter = Counter(error_messages)
        recurring = []
        
        for error, count in error_counter.items():
            if count >= min_occurrences:
                recurring.append({
                    'error': error,
                    'occurrences': count,
                    'first_seen': 'Unknown',  # Could be enhanced to track timestamps
                    'category': self._categorize_error(error)
                })
        
        return sorted(recurring, key=lambda x: x['occurrences'], reverse=True)
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize an error message."""
        error_lower = error_message.lower()
        
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    return category.replace('_', ' ').title()
        
        return "Unclassified"
    
    def generate_report(self, days: int = 7) -> str:
        """Generate a comprehensive error analysis report."""
        log_files = self.get_recent_logs(days)
        
        if not log_files:
            return f"No log files found in {self.logs_dir} for the last {days} days."
        
        # Run analyses
        pattern_analysis = self.analyze_error_patterns(log_files)
        recurring_errors = self.find_recurring_errors(log_files)
        
        # Generate report
        report = []
        report.append(f"# AD-HDTV Error Analysis Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Period: Last {days} days")
        report.append(f"Log files analyzed: {len(log_files)}")
        report.append("")
        
        # Error patterns summary
        report.append("## Error Patterns Summary")
        if pattern_analysis['pattern_counts']:
            for category, count in sorted(pattern_analysis['pattern_counts'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {category.replace('_', ' ').title()}: {count} occurrences")
        else:
            report.append("No error patterns detected.")
        report.append("")
        
        # Severity breakdown
        if pattern_analysis['severity_counts']:
            report.append("## Error Severity Breakdown")
            for severity, count in sorted(pattern_analysis['severity_counts'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {severity}: {count} errors")
            report.append("")
        
        # Recurring errors
        report.append("## Most Frequent Errors")
        if recurring_errors:
            for i, error in enumerate(recurring_errors[:10], 1):
                report.append(f"{i}. **{error['category']}** ({error['occurrences']} times)")
                report.append(f"   {error['error'][:100]}{'...' if len(error['error']) > 100 else ''}")
                report.append("")
        else:
            report.append("No recurring errors found.")
        
        # Recommendations
        report.append("## Recommendations")
        
        if pattern_analysis['pattern_counts'].get('vlc_errors', 0) > 5:
            report.append("⚠️  **High VLC error count detected**")
            report.append("   - Review VLC initialization arguments")
            report.append("   - Check for widget timing issues")
            report.append("   - Verify VLC library installation")
            report.append("")
        
        if pattern_analysis['pattern_counts'].get('network_errors', 0) > 10:
            report.append("🌐 **Network issues detected**")
            report.append("   - Increase timeout values")
            report.append("   - Add retry logic for failed requests")
            report.append("   - Validate stream URLs before loading")
            report.append("")
        
        if pattern_analysis['pattern_counts'].get('audio_errors', 0) > 3:
            report.append("🔊 **Audio problems detected**")
            report.append("   - Increase VLC audio buffering")
            report.append("   - Use platform-specific audio output")
            report.append("   - Test with different audio codecs")
            report.append("")
        
        if not pattern_analysis['pattern_counts']:
            report.append("✅ No significant error patterns detected. Application appears stable.")
        
        return "\n".join(report)
    
    def get_error_statistics(self) -> Dict:
        """Get current error statistics."""
        log_files = self.get_recent_logs()
        total_errors = 0
        critical_errors = 0
        
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_errors += content.upper().count('ERROR')
                    critical_errors += content.upper().count('CRITICAL')
            except Exception:
                continue
        
        return {
            'total_errors': total_errors,
            'critical_errors': critical_errors,
            'log_files_count': len(log_files),
            'analysis_date': datetime.now().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(description='Analyze AD-HDTV error logs')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--logs-dir', default='logs', help='Directory containing log files (default: logs)')
    parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format (default: text)')
    parser.add_argument('--stats-only', action='store_true', help='Show only statistics')
    
    args = parser.parse_args()
    
    analyzer = ErrorAnalyzer(args.logs_dir)
    
    if args.stats_only:
        stats = analyzer.get_error_statistics()
        if args.format == 'json':
            print(json.dumps(stats, indent=2))
        else:
            print(f"Error Statistics (Last {args.days} days):")
            print(f"  Total errors: {stats['total_errors']}")
            print(f"  Critical errors: {stats['critical_errors']}")
            print(f"  Log files: {stats['log_files_count']}")
            print(f"  Analysis date: {stats['analysis_date']}")
    else:
        report = analyzer.generate_report(args.days)
        if args.format == 'json':
            # Convert report to structured data for JSON
            print(json.dumps({"report": report, "timestamp": datetime.now().isoformat()}, indent=2))
        else:
            print(report)


if __name__ == '__main__':
    main()
