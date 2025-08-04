#!/usr/bin/env python3
"""API endpoints for serving dashboard data to frontend applications."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from src.api.client import GitLabClient
from src.services.group_enhancement import GroupEnhancementService
from src.services.branch_service import BranchService
from src.services.issue_service import IssueService
from scripts.generate_executive_dashboard import (
    analyze_groups, 
    collect_issue_analytics,
    generate_ai_recommendations,
    analyze_team_performance,
    collect_all_issues,
    DEFAULT_GROUPS
)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global cache for dashboard data
dashboard_cache = {}
cache_timestamp = None
CACHE_DURATION = 300  # 5 minutes

def get_env_or_default(key: str, default: str = "") -> str:
    """Get environment variable or return default."""
    return os.getenv(key, default)

def is_cache_valid() -> bool:
    """Check if cached data is still valid."""
    global cache_timestamp
    if cache_timestamp is None:
        return False
    
    age = (datetime.now() - cache_timestamp).total_seconds()
    return age < CACHE_DURATION

def get_gitlab_config() -> tuple:
    """Get GitLab configuration from environment."""
    gitlab_url = get_env_or_default('GITLAB_URL')
    gitlab_token = get_env_or_default('GITLAB_TOKEN')
    
    if not gitlab_url or not gitlab_token:
        raise ValueError("Missing GITLAB_URL or GITLAB_TOKEN environment variables")
    
    return gitlab_url, gitlab_token

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/dashboard/data', methods=['GET'])
def get_dashboard_data():
    """Get complete dashboard data."""
    try:
        # Check cache first
        if is_cache_valid() and dashboard_cache:
            return jsonify({
                'status': 'success',
                'data': dashboard_cache,
                'cached': True,
                'timestamp': cache_timestamp.isoformat()
            })
        
        # Get parameters
        group_ids_str = request.args.get('groups', '')
        days = int(request.args.get('days', 30))
        team_name = request.args.get('team_name', 'Development Team')
        
        # Parse group IDs
        if group_ids_str:
            group_ids = [int(gid.strip()) for gid in group_ids_str.split(',')]
        else:
            # Use default groups if none specified
            group_ids = list(DEFAULT_GROUPS.keys())
        
        # Get GitLab config
        gitlab_url, gitlab_token = get_gitlab_config()
        
        # Generate dashboard data
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, days)
        
        # Add metadata
        report_data['api_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'team_name': team_name,
            'groups_analyzed': group_ids,
            'period_days': days
        }
        
        # Cache the data
        global dashboard_cache, cache_timestamp
        dashboard_cache = report_data
        cache_timestamp = datetime.now()
        
        return jsonify({
            'status': 'success',
            'data': report_data,
            'cached': False,
            'timestamp': cache_timestamp.isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary data only."""
    try:
        # Get parameters
        group_ids_str = request.args.get('groups', '')
        days = int(request.args.get('days', 30))
        
        # Parse group IDs
        if group_ids_str:
            group_ids = [int(gid.strip()) for gid in group_ids_str.split(',')]
        else:
            # Use default groups if none specified
            group_ids = list(DEFAULT_GROUPS.keys())
        
        # Get GitLab config
        gitlab_url, gitlab_token = get_gitlab_config()
        
        # Generate summary data only
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, days)
        
        summary_data = {
            'summary': report_data['summary'],
            'metadata': report_data['metadata'],
            'groups_count': len(report_data['groups']),
            'projects_count': len(report_data['projects']),
            'contributors_count': len(report_data['contributors']),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': summary_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/dashboard/projects', methods=['GET'])
def get_projects_data():
    """Get projects data only."""
    try:
        # Get parameters
        group_ids_str = request.args.get('groups', '')
        days = int(request.args.get('days', 30))
        
        # Parse group IDs
        if group_ids_str:
            group_ids = [int(gid.strip()) for gid in group_ids_str.split(',')]
        else:
            # Use default groups if none specified
            group_ids = list(DEFAULT_GROUPS.keys())
        
        # Get GitLab config
        gitlab_url, gitlab_token = get_gitlab_config()
        
        # Generate projects data
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, days)
        
        projects_data = {
            'projects': report_data['projects'],
            'groups': report_data['groups'],
            'technology_stack': dict(report_data['technology_stack']),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': projects_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/dashboard/issues', methods=['GET'])
def get_issues_data():
    """Get issues data only."""
    try:
        # Get parameters
        group_ids_str = request.args.get('groups', '')
        days = int(request.args.get('days', 30))
        
        # Parse group IDs
        if group_ids_str:
            group_ids = [int(gid.strip()) for gid in group_ids_str.split(',')]
        else:
            # Use default groups if none specified
            group_ids = list(DEFAULT_GROUPS.keys())
        
        # Get GitLab config
        gitlab_url, gitlab_token = get_gitlab_config()
        
        # Generate issues data
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, days)
        
        issues_data = {
            'all_issues': report_data['all_issues'],
            'issue_analytics': report_data['issue_analytics'],
            'ai_recommendations': report_data['ai_recommendations'],
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': issues_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/dashboard/team', methods=['GET'])
def get_team_data():
    """Get team performance data only."""
    try:
        # Get parameters
        group_ids_str = request.args.get('groups', '')
        days = int(request.args.get('days', 30))
        
        # Parse group IDs
        if group_ids_str:
            group_ids = [int(gid.strip()) for gid in group_ids_str.split(',')]
        else:
            # Use default groups if none specified
            group_ids = list(DEFAULT_GROUPS.keys())
        
        # Get GitLab config
        gitlab_url, gitlab_token = get_gitlab_config()
        
        # Generate team data
        report_data = analyze_groups(group_ids, gitlab_url, gitlab_token, days)
        
        team_data = {
            'team_analytics': report_data['team_analytics'],
            'contributors': dict(report_data['contributors']),
            'daily_activity': dict(report_data['daily_activity']),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': team_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear dashboard cache."""
    global dashboard_cache, cache_timestamp
    dashboard_cache = {}
    cache_timestamp = None
    
    return jsonify({
        'status': 'success',
        'message': 'Cache cleared successfully'
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get API configuration."""
    gitlab_url = get_env_or_default('GITLAB_URL')
    
    return jsonify({
        'gitlab_url': gitlab_url,
        'cache_duration': CACHE_DURATION,
        'version': '1.0.0'
    })

if __name__ == '__main__':
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    port = int(os.getenv('DASHBOARD_API_PORT', 5000))
    debug = os.getenv('DASHBOARD_API_DEBUG', 'false').lower() == 'true'
    
    print(f"🚀 Starting Dashboard API on port {port}")
    print(f"📊 Available endpoints:")
    print(f"   GET  /api/health - Health check")
    print(f"   GET  /api/dashboard/data - Complete dashboard data")
    print(f"   GET  /api/dashboard/summary - Summary data only")
    print(f"   GET  /api/dashboard/projects - Projects data only")
    print(f"   GET  /api/dashboard/issues - Issues data only")
    print(f"   GET  /api/dashboard/team - Team data only")
    print(f"   POST /api/cache/clear - Clear cache")
    print(f"   GET  /api/config - API configuration")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 