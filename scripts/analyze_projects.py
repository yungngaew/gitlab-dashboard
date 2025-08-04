#!/usr/bin/env python3
"""Generate analytics reports for GitLab projects and groups."""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import GitLabClient
from src.services import GitLabAnalytics
from src.services.analytics_advanced import AdvancedAnalytics
from src.utils import Config, setup_logging, get_logger
from src.utils.logger import Colors
from src.utils.cache import FileCache, CachedAnalytics

logger = get_logger(__name__)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate analytics reports for GitLab projects"
    )
    
    # Target selection
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        '--project', '-p',
        help='Project ID or path to analyze'
    )
    target_group.add_argument(
        '--group', '-g',
        help='Group ID or name to analyze'
    )
    target_group.add_argument(
        '--compare', '-cmp',
        nargs='+',
        help='Compare multiple projects (provide project IDs)'
    )
    
    # Analytics options
    parser.add_argument(
        '--trends',
        action='store_true',
        help='Include trend analysis'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days for trend analysis (default: 30)'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML dashboard'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json', 'text', 'html'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    # Cache options
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear cache before running'
    )
    
    # Configuration
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config)
    
    # Setup logging
    setup_logging(
        config.get_log_config(),
        console_level=args.log_level
    )
    
    try:
        # Validate configuration
        config.validate()
        
        # Create GitLab client
        gitlab_config = config.get_gitlab_config()
        client = GitLabClient(
            url=gitlab_config['url'],
            token=gitlab_config['token'],
            config=gitlab_config
        )
        
        # Create analytics services
        analytics = GitLabAnalytics(client)
        advanced = AdvancedAnalytics(client)
        
        # Set up caching if enabled
        cache = None
        if not args.no_cache:
            cache = FileCache()
            if args.clear_cache:
                cache.clear()
                print(f"{Colors.YELLOW}Cache cleared{Colors.RESET}")
            
            # Wrap analytics with cache
            analytics = CachedAnalytics(analytics, cache)
            advanced = CachedAnalytics(advanced, cache)
        
        # Get metrics
        print(f"{Colors.BOLD}Generating analytics report...{Colors.RESET}")
        
        if args.compare:
            # Project comparison mode
            logger.info(f"Comparing projects: {args.compare}")
            metrics = advanced.compare_projects(args.compare)
            
            if args.html or args.format == 'html':
                report = advanced.generate_html_dashboard(metrics)
            else:
                # Use basic report generation for comparison
                report = json.dumps(metrics, indent=2, default=str) if args.format == 'json' else str(metrics)
        
        elif args.project:
            logger.info(f"Analyzing project: {args.project}")
            
            if args.trends:
                # Get trend analysis
                metrics = advanced.get_project_trends(args.project, days=args.days)
                
                if args.html or args.format == 'html':
                    report = advanced.generate_html_dashboard(metrics)
                else:
                    # Enhance with basic metrics
                    basic_metrics = analytics.get_project_metrics(args.project)
                    metrics['basic_metrics'] = basic_metrics
                    report = analytics.generate_summary_report(metrics, format=args.format)
            else:
                # Basic metrics
                metrics = analytics.get_project_metrics(args.project)
                report = analytics.generate_summary_report(metrics, format=args.format)
        
        else:
            logger.info(f"Analyzing group: {args.group}")
            
            # Find group by name if needed
            if not args.group.isdigit():
                group = client.search_group_by_name(args.group)
                if not group:
                    print(f"{Colors.RED}Error: Group '{args.group}' not found{Colors.RESET}")
                    return 1
                group_id = group['id']
            else:
                group_id = args.group
            
            metrics = analytics.get_group_metrics(group_id)
            report = analytics.generate_summary_report(metrics, format=args.format)
        
        # Output report
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine file extension if not provided
            if not output_path.suffix:
                ext_map = {'markdown': '.md', 'json': '.json', 'html': '.html', 'text': '.txt'}
                output_path = output_path.with_suffix(ext_map.get(args.format, '.txt'))
            
            with open(output_path, 'w') as f:
                f.write(report)
            
            print(f"{Colors.GREEN}Report saved to: {output_path}{Colors.RESET}")
        else:
            print(f"\n{report}")
        
        # Summary statistics for trends
        if args.trends and 'health_score' in metrics and args.format != 'json':
            print(f"\n{Colors.BOLD}Health Analysis:{Colors.RESET}")
            health = metrics['health_score']
            print(f"- Overall Score: {health['score']}/100 (Grade: {health['grade']})")
            if health.get('recommendations'):
                print(f"\n{Colors.BOLD}Recommendations:{Colors.RESET}")
                for rec in health['recommendations']:
                    print(f"  {rec}")
        
        # Cache statistics
        if cache and not args.no_cache:
            stats = cache.get_stats()
            logger.debug(f"Cache stats: {stats['total_entries']} entries, {stats['total_size_bytes']} bytes")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate analytics: {e}", exc_info=True)
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())