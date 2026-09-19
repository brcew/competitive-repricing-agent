"""
Generate daily cost comparison report.

This script generates and displays/saves a daily cost comparison report
showing the cost savings of the two-tier approach vs single large model.

Usage:
    python generate_daily_report.py               # Display to console
    python generate_daily_report.py --save        # Save to file
    python generate_daily_report.py --both        # Both console and file
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import sys
from datetime import datetime
from cost_comparison import get_cost_comparison_generator


def main():
    """Generate daily cost report."""
    # Parse command line arguments
    save_to_file = '--save' in sys.argv or '--both' in sys.argv
    show_console = '--save' not in sys.argv or '--both' in sys.argv
    
    # Generate report
    generator = get_cost_comparison_generator()
    summary = generator.generate_daily_summary()
    
    # Display to console
    if show_console:
        generator.print_summary(summary)
    
    # Save to file
    if save_to_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"cost_report_{timestamp}.txt"
        generator.save_summary_to_file(filename, summary)
        print(f"\n✅ Report saved to: {filename}\n")
    
    # Return summary for programmatic use
    return summary


if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    main()
