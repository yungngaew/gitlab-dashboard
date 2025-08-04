from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from database import DatabaseManager
from gitlab_api import normalize_contributor_name, build_contributor_mapping
import traceback

class DataTransformer:
    """แปลงข้อมูลจาก GitLab API เป็นรูปแบบที่เหมาะสมกับฐานข้อมูล"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.name_mapping, self.email_mapping = build_contributor_mapping()
    
    def transform_and_save_groups(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูลกลุ่ม"""
        try:
            for group_id, group_data in report_data['groups'].items():
                # สร้างข้อมูลสำหรับ group_cache
                group_cache_data = {
                    'id': int(group_id),
                    'name': group_data['name'],
                    'path': group_data.get('path', ''),
                    'health_grade': group_data['health_grade'],
                    'total_commits': group_data['total_commits'],
                    'total_issues': group_data['total_issues'],
                    'total_mrs': group_data['total_mrs'],
                    'active_users': group_data['active_projects']
                }
                
                print("[DEBUG] group_cache_data:", group_cache_data)
                if not self.db.upsert_group_cache(group_cache_data):
                    print(f"[ERROR] Failed to save group cache for {group_data['name']}")
                    return False
            
            print(f"[INFO] Successfully saved {len(report_data['groups'])} groups to database")
            return True
            
        except Exception as e:            
            print(f"[ERROR] Failed to transform and save groups: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_projects(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูลโปรเจกต์"""
        try:
            for project in report_data['projects']:
                # หา group_id หลัก (ใช้ group แรกที่ project อยู่)
                primary_group_id = None
                if project.get('groups'):
                    primary_group_id = project['groups'][0]  # ใช้ group แรก
                
                # สร้างข้อมูลสำหรับ project_cache
                project_cache_data = {
                    'id': project['id'],
                    'name': project['name'],
                    'name_with_namespace': project.get('path', ''),
                    'path_with_namespace': project.get('path', ''),
                    'description': project.get('description', ''),
                    'status': project.get('status', 'active'),
                    'health_grade': project.get('health_grade', 'D'),
                    'open_issues': project.get('open_issues', 0),
                    'mrs_created': project.get('mrs_created', 0),
                    'commits_30d': project.get('commits_30d', 0),
                    'contributors_30d': project.get('contributors_30d', 0),
                    'last_activity': project.get('last_activity'),
                    'group_id': primary_group_id,
                    'group_name': ','.join(str(g) for g in project.get('groups', [])) if project.get('groups') else None
                }
                
                if not self.db.upsert_project_cache(project_cache_data):
                    print(f"[ERROR] Failed to save project cache for {project['name']}")
                    return False
            
            print(f"[INFO] Successfully saved {len(report_data['projects'])} projects to database")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save projects: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_team_members(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูลสมาชิกทีม"""
        try:
            team_analytics = report_data.get('team_analytics', {})
            
            for member_name, member_data in team_analytics.items():
                # สร้างข้อมูลสำหรับ team_member_cache
                member_cache_data = {
                    'name': member_name,
                    'email': f"{member_name.lower().replace(' ', '.')}@example.com",  # Placeholder email
                    'commits': member_data.get('commits', 0),
                    'issues_assigned': member_data.get('issues_assigned', 0),
                    'issues_resolved': member_data.get('issues_resolved', 0),
                    'merge_requests': member_data.get('merge_requests', 0),
                    'last_activity': member_data.get('recent_activity', [{}])[0].get('date') if member_data.get('recent_activity') else None
                }
                
                if not self.db.upsert_team_member_cache(member_cache_data):
                    print(f"[ERROR] Failed to save team member cache for {member_name}")
                    return False
                
                # บันทึกความสัมพันธ์กับโปรเจกต์
                for project_name in member_data.get('projects', []):
                    # หา project_id จากชื่อโปรเจกต์
                    project_id = None
                    for project in report_data['projects']:
                        if project['name'] == project_name:
                            project_id = project['id']
                            break
                    
                    if project_id:
                        member_id = hash(member_cache_data['email']) % 2147483647
                        self.db.upsert_team_member_project(member_id, project_id)
            
            print(f"[INFO] Successfully saved {len(team_analytics)} team members to database")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save team members: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_issues(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูล issue"""
        try:
            all_issues = report_data.get('all_issues', [])
            
            for issue in all_issues:
                # สร้างข้อมูลสำหรับ issue_cache
                issue_cache_data = {
                    'id': issue['id'],
                    'iid': issue.get('iid', issue['id']),
                    'project_id': issue['project_id'],
                    'project_name': issue['project_name'],
                    'title': issue['title'],
                    'description': issue.get('description', ''),
                    'state': issue.get('state', 'opened'),
                    'priority': issue.get('priority', 'medium'),
                    'assignee_email': issue.get('assignee', {}).get('email'),
                    'assignee_name': issue.get('assignee', {}).get('name', ''),
                    'author_name': issue.get('author', {}).get('name', ''),
                    'created_at': issue.get('created_at'),
                    'updated_at': issue.get('updated_at'),
                    'closed_at': issue.get('closed_at'),
                    'due_date': issue.get('due_date'),
                    'labels': issue.get('labels', [])
                }
                
                if not self.db.upsert_issue_cache(issue_cache_data):
                    print(f"[ERROR] Failed to save issue cache for {issue['title']}")
                    return False
            
            print(f"[INFO] Successfully saved {len(all_issues)} issues to database")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save issues: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_kpi(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูล KPI"""
        try:
            summary = report_data['summary']
            
            kpi_data = {
                'total_commits': summary.get('total_commits', 0),
                'total_mrs': summary.get('total_mrs', 0),
                'total_issues': summary.get('total_issues', 0),
                'active_projects': summary.get('active_projects', 0),
                'period': '30d'  # Default period
            }
            
            if not self.db.upsert_kpi_cache(kpi_data):
                print("[ERROR] Failed to save KPI cache")
                return False
            
            print("[INFO] Successfully saved KPI data to database")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save KPI: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_activity(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูลกิจกรรมรายวัน"""
        try:
            daily_activity = report_data.get('daily_activity', {})
            
            for date_str, commits in daily_activity.items():
                # สร้างข้อมูลสำหรับ activity_cache
                activity_data = {
                    'date': date_str,
                    'commits': commits,
                    'issues_created': 0,  # ต้องคำนวณจากข้อมูล issue
                    'issues_closed': 0,   # ต้องคำนวณจากข้อมูล issue
                    'mrs_created': 0,     # ต้องคำนวณจากข้อมูล MR
                    'mrs_merged': 0       # ต้องคำนวณจากข้อมูล MR
                }
                
                if not self.db.upsert_activity_cache(activity_data):
                    print(f"[ERROR] Failed to save activity cache for {date_str}")
                    return False
            
            print(f"[INFO] Successfully saved {len(daily_activity)} daily activities to database")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save activity: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_dashboard_cache(self, report_data: Dict[str, Any], 
                                         cache_id: str = None) -> bool:
        """แปลงและบันทึกข้อมูล dashboard cache"""
        try:
            if cache_id is None:
                cache_id = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # บันทึกข้อมูลทั้งหมดเป็น JSON
            if not self.db.upsert_dashboard_cache(
                cache_id=cache_id,
                data_type='full_report',
                data=report_data,
                source='gitlab_api',
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            ):
                print("[ERROR] Failed to save dashboard cache")
                return False
            
            print(f"[INFO] Successfully saved dashboard cache with ID: {cache_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to transform and save dashboard cache: {e}")
            traceback.print_exc()
            return False
    
    def save_all_data(self, report_data: Dict[str, Any], save_cache: bool = True) -> bool:
        """บันทึกข้อมูลทั้งหมดลงฐานข้อมูล"""
        try:
            print("[INFO] Starting to save all data to database...")
            
            # บันทึกข้อมูลตามลำดับ (เพื่อรักษา referential integrity)
            if not self.transform_and_save_groups(report_data):
                return False
            
            if not self.transform_and_save_projects(report_data):
                return False
            
            if not self.transform_and_save_team_members(report_data):
                return False
            
            if not self.transform_and_save_issues(report_data):
                return False
            
            if not self.transform_and_save_kpi(report_data):
                return False
            
            if not self.transform_and_save_activity(report_data):
                return False
            
            if save_cache:
                if not self.transform_and_save_dashboard_cache(report_data):
                    return False
            
            print("[SUCCESS] All data saved to database successfully!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to save all data: {e}")
            traceback.print_exc()
            return False 