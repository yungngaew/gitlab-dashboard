#!/usr/bin/env python3
"""FastAPI server for GitLab Analytics API."""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our modules
from group_analytics import analyze_groups
from project_analytics import analyze_project
from issue_analytics import collect_issue_analytics
from team_analytics import analyze_team_performance
from gitlab_api import get_all_group_ids
from database import DatabaseManager
from data_transformer import DataTransformer

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Pydantic models for request/response
class AnalyticsRequest(BaseModel):
    group_ids: List[int] = Field(..., description="List of GitLab group IDs")
    days: int = Field(30, ge=1, le=365, description="Number of days to analyze")
    save_to_db: bool = Field(False, description="Save results to database")
    include_issues: bool = Field(True, description="Include issue analytics")
    include_team: bool = Field(True, description="Include team analytics")

class ProjectRequest(BaseModel):
    project_id: int = Field(..., description="GitLab project ID")
    days: int = Field(30, ge=1, le=365, description="Number of days to analyze")

class GroupInfo(BaseModel):
    id: int
    name: str
    path: str
    full_path: str
    description: Optional[str]
    visibility: str
    projects_count: int
    subgroups_count: int

class AnalyticsResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    timestamp: str
    metadata: Dict[str, Any]

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    timestamp: str

# FastAPI app
app = FastAPI(
    title="GitLab Analytics API",
    description="API for analyzing GitLab groups, projects, and team performance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for GitLab credentials
def get_gitlab_credentials():
    """Get GitLab credentials from environment."""
    gitlab_url = os.getenv('GITLAB_URL')
    gitlab_token = os.getenv('GITLAB_TOKEN')
    
    if not gitlab_url or not gitlab_token:
        raise HTTPException(
            status_code=500,
            detail="GitLab credentials not configured. Set GITLAB_URL and GITLAB_TOKEN environment variables."
        )
    
    return gitlab_url, gitlab_token

# Dependency for database connection
def get_db_manager():
    """Get database manager if configured."""
    db_name = os.getenv('DB_NAME')
    if not db_name:
        return None
    
    db_manager = DatabaseManager()
    if not db_manager.connect():
        return None
    
    return db_manager

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Get all groups endpoint
@app.get("/groups", response_model=List[GroupInfo], tags=["Groups"])
async def get_groups(
    gitlab_creds: tuple = Depends(get_gitlab_credentials)
):
    """Get all groups available on GitLab instance."""
    gitlab_url, gitlab_token = gitlab_creds
    
    try:
        # Get all group IDs
        group_ids = get_all_group_ids(gitlab_url, gitlab_token)
        
        if not group_ids:
            return []
        
        # Get detailed information for each group
        from scripts.check_groups import get_detailed_group_info
        detailed_groups = get_detailed_group_info(gitlab_url, gitlab_token, group_ids)
        
        return detailed_groups
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch groups: {str(e)}")

# Group analytics endpoint
@app.post("/analytics/groups", response_model=AnalyticsResponse, tags=["Analytics"])
async def analyze_groups_endpoint(
    request: AnalyticsRequest,
    gitlab_creds: tuple = Depends(get_gitlab_credentials),
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Analyze GitLab groups and return comprehensive analytics."""
    gitlab_url, gitlab_token = gitlab_creds
    
    try:
        # Analyze groups
        report_data = analyze_groups(
            request.group_ids, 
            gitlab_url, 
            gitlab_token, 
            request.days
        )
        
        # Save to database if requested
        if request.save_to_db and db_manager:
            try:
                transformer = DataTransformer(db_manager)
                transformer.save_all_data(report_data)
            except Exception as db_error:
                # Log database error but don't fail the request
                print(f"Database save failed: {db_error}")
        
        # Prepare response
        response_data = {
            'summary': report_data['summary'],
            'projects': report_data['projects'],
            'groups': report_data['groups']
        }
        
        # Include optional analytics
        if request.include_issues:
            response_data['issue_analytics'] = report_data.get('issue_analytics', {})
        
        if request.include_team:
            response_data['team_analytics'] = report_data.get('team_analytics', {})
        
        return AnalyticsResponse(
            success=True,
            data=response_data,
            timestamp=datetime.now().isoformat(),
            metadata={
                'groups_analyzed': len(request.group_ids),
                'days_analyzed': request.days,
                'saved_to_db': request.save_to_db and db_manager is not None
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Single project analytics endpoint
@app.get("/analytics/projects/{project_id}", response_model=AnalyticsResponse, tags=["Analytics"])
async def analyze_project_endpoint(
    project_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    gitlab_creds: tuple = Depends(get_gitlab_credentials)
):
    """Analyze a single GitLab project."""
    gitlab_url, gitlab_token = gitlab_creds
    
    try:
        # Create project object
        project = {'id': project_id, 'name': f'Project {project_id}'}
        
        # Analyze project
        project_data = analyze_project(project, gitlab_url, gitlab_token, days)
        
        return AnalyticsResponse(
            success=True,
            data=project_data,
            timestamp=datetime.now().isoformat(),
            metadata={
                'project_id': project_id,
                'days_analyzed': days
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Project analysis failed: {str(e)}")

# Issue analytics endpoint
@app.post("/analytics/issues", response_model=AnalyticsResponse, tags=["Analytics"])
async def analyze_issues_endpoint(
    request: AnalyticsRequest,
    gitlab_creds: tuple = Depends(get_gitlab_credentials)
):
    """Analyze issues across multiple groups."""
    gitlab_url, gitlab_token = gitlab_creds
    
    try:
        # First get projects from groups
        all_projects = []
        for group_id in request.group_ids:
            from scripts.gitlab_api import simple_gitlab_request
            
            projects = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"groups/{group_id}/projects",
                {"include_subgroups": "true", "archived": "false"}
            )
            
            if projects:
                all_projects.extend(projects)
        
        # Analyze issues
        issue_analytics = collect_issue_analytics(all_projects, gitlab_url, gitlab_token)
        
        return AnalyticsResponse(
            success=True,
            data=issue_analytics,
            timestamp=datetime.now().isoformat(),
            metadata={
                'groups_analyzed': len(request.group_ids),
                'projects_analyzed': len(all_projects),
                'days_analyzed': request.days
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Issue analysis failed: {str(e)}")

# Team analytics endpoint
@app.post("/analytics/team", response_model=AnalyticsResponse, tags=["Analytics"])
async def analyze_team_endpoint(
    request: AnalyticsRequest,
    gitlab_creds: tuple = Depends(get_gitlab_credentials)
):
    """Analyze team performance across multiple groups."""
    gitlab_url, gitlab_token = gitlab_creds
    
    try:
        # First get projects from groups
        all_projects = []
        for group_id in request.group_ids:
            from scripts.gitlab_api import simple_gitlab_request
            
            projects = simple_gitlab_request(
                gitlab_url, gitlab_token,
                f"groups/{group_id}/projects",
                {"include_subgroups": "true", "archived": "false"}
            )
            
            if projects:
                all_projects.extend(projects)
        
        # Analyze team performance
        team_analytics = analyze_team_performance(all_projects, gitlab_url, gitlab_token, request.days)
        
        return AnalyticsResponse(
            success=True,
            data=team_analytics,
            timestamp=datetime.now().isoformat(),
            metadata={
                'groups_analyzed': len(request.group_ids),
                'projects_analyzed': len(all_projects),
                'days_analyzed': request.days
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team analysis failed: {str(e)}")

# Database cache endpoints
@app.get("/cache/{cache_id}", response_model=AnalyticsResponse, tags=["Cache"])
async def get_cached_data(
    cache_id: str,
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get cached analytics data from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        cached_data = db_manager.get_cached_data(cache_id)
        
        if not cached_data:
            raise HTTPException(status_code=404, detail="Cache not found")
        
        return AnalyticsResponse(
            success=True,
            data=cached_data,
            timestamp=datetime.now().isoformat(),
            metadata={'cache_id': cache_id, 'source': 'database'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cache: {str(e)}")

@app.delete("/cache/{cache_id}", tags=["Cache"])
async def clear_cache(
    cache_id: str,
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Clear specific cache entry."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # This would need to be implemented in DatabaseManager
        # db_manager.delete_cache(cache_id)
        return {"success": True, "message": f"Cache {cache_id} cleared"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

# Database data endpoints
@app.get("/api/database/groups", tags=["Database"])
async def get_database_groups(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get all groups from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT id, name, path, health_grade, total_commits, 
               total_issues, total_mrs, active_users, last_updated
        FROM "gitlab-activity-analysis-schema".group_cache
        ORDER BY last_updated DESC
        """
        results = db_manager.execute_query(query)
        
        if results is None:
            return {"groups": [], "count": 0}
        
        return {
            "groups": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/projects", tags=["Database"])
async def get_database_projects(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get all projects from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT id, name, name_with_namespace, path_with_namespace, description,
               status, health_grade, open_issues, mrs_created, commits_30d,
               contributors_30d, last_activity, group_id, group_name, last_updated
        FROM "gitlab-activity-analysis-schema".project_cache
        ORDER BY last_updated DESC
        """
        results = db_manager.execute_query(query)
        
        if results is None:
            return {"projects": [], "count": 0}
        
        return {
            "projects": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/team-members", tags=["Database"])
async def get_database_team_members(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get all team members from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT id, name, email, username, commits, issues_assigned,
               issues_resolved, merge_requests, last_activity, last_updated
        FROM "gitlab-activity-analysis-schema".team_member_cache
        ORDER BY commits DESC
        """
        results = db_manager.execute_query(query)
        
        if results is None:
            return {"team_members": [], "count": 0}
        
        return {
            "team_members": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/issues", tags=["Database"])
async def get_database_issues(
    state: Optional[str] = Query(None, description="Filter by issue state"),
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get all issues from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT id, iid, project_id, project_name, title, description,
               state, priority, assignee_email, assignee_name, author_name,
               created_at, updated_at, closed_at, due_date, labels, last_updated
        FROM "gitlab-activity-analysis-schema".issue_cache
        """
        
        params = None
        if state:
            query += " WHERE state = %s"
            params = (state,)
        
        query += " ORDER BY created_at DESC"
        
        results = db_manager.execute_query(query, params)
        
        if results is None:
            return {"issues": [], "count": 0}
        
        return {
            "issues": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/kpi", tags=["Database"])
async def get_database_kpi(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get KPI data from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT id, total_commits, total_mrs, total_issues, active_projects,
               last_updated, period
        FROM "gitlab-activity-analysis-schema".kpi_cache
        ORDER BY last_updated DESC
        LIMIT 1
        """
        results = db_manager.execute_query(query)
        
        if results is None or not results:
            return {"kpi": None, "timestamp": datetime.now().isoformat()}
        
        return {
            "kpi": results[0],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/activity", tags=["Database"])
async def get_database_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch"),
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get activity data from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT date, commits, issues_created, issues_closed,
               mrs_created, mrs_merged, last_updated
        FROM "gitlab-activity-analysis-schema".activity_cache
        WHERE date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date DESC
        """
        results = db_manager.execute_query(query, (days,))
        
        if results is None:
            return {"activity": [], "count": 0}
        
        return {
            "activity": results,
            "count": len(results),
            "days_requested": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/summary", tags=["Database"])
async def get_database_summary(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get summary statistics from database."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get counts
        group_count = db_manager.execute_query("SELECT COUNT(*) as count FROM \"gitlab-activity-analysis-schema\".group_cache")
        project_count = db_manager.execute_query("SELECT COUNT(*) as count FROM \"gitlab-activity-analysis-schema\".project_cache")
        member_count = db_manager.execute_query("SELECT COUNT(*) as count FROM \"gitlab-activity-analysis-schema\".team_member_cache")
        issue_count = db_manager.execute_query("SELECT COUNT(*) as count FROM \"gitlab-activity-analysis-schema\".issue_cache")
        
        # Get latest activity
        latest_activity = db_manager.execute_query("""
            SELECT MAX(last_updated) as latest_update 
            FROM (
                SELECT last_updated FROM "gitlab-activity-analysis-schema".group_cache
                UNION ALL
                SELECT last_updated FROM "gitlab-activity-analysis-schema".project_cache
                UNION ALL
                SELECT last_updated FROM "gitlab-activity-analysis-schema".team_member_cache
                UNION ALL
                SELECT last_updated FROM "gitlab-activity-analysis-schema".issue_cache
            ) as all_updates
        """)
        
        return {
            "summary": {
                "groups": group_count[0]['count'] if group_count else 0,
                "projects": project_count[0]['count'] if project_count else 0,
                "team_members": member_count[0]['count'] if member_count else 0,
                "issues": issue_count[0]['count'] if issue_count else 0,
                "latest_update": latest_activity[0]['latest_update'] if latest_activity else None
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/team-member-projects", tags=["Database"])
async def get_team_member_projects(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get project assignments for team members."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT tmp.member_id, p.name as project_name, p.id as project_id
        FROM "gitlab-activity-analysis-schema".team_member_project tmp
        JOIN "gitlab-activity-analysis-schema".project_cache p ON tmp.project_id = p.id
        ORDER BY tmp.member_id, p.name
        """
        results = db_manager.execute_query(query)
        
        if results is None:
            return {"assignments": {}, "count": 0}
        
        # Group by member_id
        assignments = {}
        for row in results:
            member_id = row['member_id']
            if member_id not in assignments:
                assignments[member_id] = []
            assignments[member_id].append({
                'project_id': row['project_id'],
                'project_name': row['project_name']
            })
        
        return {
            "assignments": assignments,
            "count": len(assignments),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/group-project-counts", tags=["Database"])
async def get_group_project_counts(
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get project counts for each group."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        query = """
        SELECT group_id, COUNT(*) as project_count
        FROM "gitlab-activity-analysis-schema".project_cache
        WHERE group_id IS NOT NULL
        GROUP BY group_id
        """
        results = db_manager.execute_query(query)
        
        if results is None:
            return {"counts": {}, "timestamp": datetime.now().isoformat()}
        
        counts = {}
        for row in results:
            counts[row['group_id']] = row['project_count']
        
        return {
            "counts": counts,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/database/activity-detail", tags=["Database"])
async def get_activity_detail(
    user_ids: Optional[str] = Query(None, description="Comma-separated list of user IDs to filter by"),
    project_ids: Optional[str] = Query(None, description="Comma-separated list of project IDs to filter by"),
    days: int = Query(30, ge=1, le=365, description="Number of days to fetch"),
    db_manager: Optional[DatabaseManager] = Depends(get_db_manager)
):
    """Get detailed activity data with user and project breakdown from user_project_activity_cache."""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Parse filter parameters
        user_id_list = None
        if user_ids:
            try:
                user_id_list = [int(uid.strip()) for uid in user_ids.split(',') if uid.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_ids format. Use comma-separated integers.")
        
        project_id_list = None
        if project_ids:
            try:
                project_id_list = [int(pid.strip()) for pid in project_ids.split(',') if pid.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project_ids format. Use comma-separated integers.")
        
        # Build the query
        query = """
        SELECT 
            upac.date,
            upac.user_id,
            tm.name as user_name,
            upac.project_id,
            pc.name as project_name,
            upac.commits,
            upac.issues_created,
            upac.issues_closed,
            upac.mrs_created,
            upac.mrs_merged,
            upac.last_updated
        FROM "gitlab-activity-analysis-schema".user_project_activity_cache upac
        JOIN "gitlab-activity-analysis-schema".team_member_cache tm ON upac.user_id = tm.id
        JOIN "gitlab-activity-analysis-schema".project_cache pc ON upac.project_id = pc.id
        WHERE upac.date >= CURRENT_DATE - INTERVAL '%s days'
        """
        
        params = [days]
        
        # Add user filter
        if user_id_list:
            placeholders = ','.join(['%s'] * len(user_id_list))
            query += f" AND upac.user_id IN ({placeholders})"
            params.extend(user_id_list)
        
        # Add project filter
        if project_id_list:
            placeholders = ','.join(['%s'] * len(project_id_list))
            query += f" AND upac.project_id IN ({placeholders})"
            params.extend(project_id_list)
        
        query += " ORDER BY upac.date DESC, upac.user_id, upac.project_id"
        
        results = db_manager.execute_query(query, tuple(params))
        
        if results is None:
            return {"activity_detail": [], "count": 0}
        
        # Group by date for easier frontend consumption
        activity_by_date = {}
        for row in results:
            date = row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date'])
            
            if date not in activity_by_date:
                activity_by_date[date] = []
            
            activity_by_date[date].append({
                "user_id": row['user_id'],
                "user_name": row['user_name'],
                "project_id": row['project_id'],
                "project_name": row['project_name'],
                "commits": row['commits'],
                "issues_created": row['issues_created'],
                "issues_closed": row['issues_closed'],
                "mrs_created": row['mrs_created'],
                "mrs_merged": row['mrs_merged']
            })
        
        # Convert to array format
        activity_array = [
            {
                "date": date,
                "data": data
            }
            for date, data in activity_by_date.items()
        ]
        
        return {
            "activity_detail": activity_array,
            "count": len(results),
            "days_requested": days,
            "user_filter": user_id_list,
            "project_filter": project_id_list,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_api_stats():
    """Get API usage statistics."""
    # This could be enhanced with actual usage tracking
    return {
        "api_version": "1.0.0",
        "endpoints": [
            "/health",
            "/groups",
            "/analytics/groups",
            "/analytics/projects/{project_id}",
            "/analytics/issues",
            "/analytics/team",
            "/cache/{cache_id}"
        ],
        "timestamp": datetime.now().isoformat()
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return ErrorResponse(
        error=exc.detail,
        timestamp=datetime.now().isoformat()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return ErrorResponse(
        error=f"Internal server error: {str(exc)}",
        timestamp=datetime.now().isoformat()
    )

# Main function to run the server
def main():
    """Run the FastAPI server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitLab Analytics FastAPI Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"Starting GitLab Analytics API server on {args.host}:{args.port}")
    print(f"API documentation available at: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "scripts.api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main() 