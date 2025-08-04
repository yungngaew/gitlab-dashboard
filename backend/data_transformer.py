from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from database import DatabaseManager
# from gitlab_api import normalize_contributor_name, build_contributor_mapping
import traceback
from collections import defaultdict

class DataTransformer:
    """แปลงข้อมูลจาก GitLab API เป็นรูปแบบที่เหมาะสมกับฐานข้อมูล"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
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
                    'active_users': group_data['active_projects'],
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
                    'last_activity': project.get('last_activity', ''),
                    'group_id': primary_group_id,
                    'group_name': ','.join(str(g) for g in project.get('groups', [])) if project.get('groups') else None,
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
        """แปลงและบันทึกข้อมูลสมาชิกทีม (ใช้ user_id จริง) พร้อม log debug"""
        try:
            all_users = report_data.get('all_users', [])
            valid_member_ids = set()
            for user_info in all_users:
                # ดึง user_id ที่เป็นตัวเลขจาก user_info โดยตรง
                int_user_id = user_info.get('id')

                # ถ้าไม่มี ID ที่เป็นตัวเลข ให้ข้ามไปเลย
                if int_user_id is None:
                    print(f"[WARNING] Skipping team member with missing ID: {user_info.get('name')}")
                    continue
                
                member_cache_data = {
                    'id': user_info.get('id'),
                    'gitlab_user_id': user_info.get('gitlab_user_id', user_info.get('id')),
                    'name': user_info.get('name', ''),
                    'email': user_info.get('email', ''),
                    'username': user_info.get('username', ''),
                    'commits': user_info.get('commits', 0),
                    'issues_assigned': user_info.get('issues_assigned', 0),
                    'issues_resolved': user_info.get('issues_resolved', 0),
                    'merge_requests': user_info.get('merge_requests', 0),
                    'last_activity': user_info.get('last_activity', ''),
                }
                
                if not self.db.upsert_team_member_cache(member_cache_data):
                    print(f"[ERROR] Failed to save team member cache for {int_user_id}")
                    # ไม่ควร return False ทันที เพื่อให้โปรแกรมทำงานต่อให้จบ
                    # return False
                
                valid_member_ids.add(int_user_id)

            print(f"[INFO] Successfully processed {len(all_users)} team members.")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to transform and save team members: {e}")
            traceback.print_exc()
            return False
    
    def transform_and_save_issues(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูล issue"""
        try:
            all_issues = report_data.get('all_issues', [])
            inserted = 0
            skipped = 0
            for issue in all_issues:
                # handle assignee (may be None)
                assignee_email = None
                assignee_name = ''
                if issue.get('assignee'):
                    assignee_email = issue['assignee'].get('email')
                    assignee_name = issue['assignee'].get('name', '')
                # log if no assignee
                if not assignee_email:
                    print(f"[INFO] Issue '{issue['title']}' has no assignee, inserting with assignee_email=NULL")
                # --- ปรับ logic state ---
                labels = [label.lower() for label in issue.get('labels', [])]
                state = issue.get('state', 'opened')
                if 'complete' in labels or 'done' in labels or 'finished' in labels:
                    state = 'closed'
                issue_cache_data = {
                    'id': issue['id'],
                    'iid': issue.get('iid', issue['id']),
                    'project_id': issue['project_id'],
                    'project_name': issue['project_name'],
                    'title': issue['title'],
                    'description': issue.get('description', ''),
                    'state': state,
                    'priority': issue.get('priority', 'medium'),
                    'assignee_email': assignee_email,  # can be None
                    'assignee_name': assignee_name,
                    'author_name': issue.get('author', {}).get('name', ''),
                    'created_at': issue.get('created_at'),
                    'updated_at': issue.get('updated_at'),
                    'closed_at': issue.get('closed_at'),
                    'due_date': issue.get('due_date'),
                    'labels': issue.get('labels', []),
                }
                if self.db.upsert_issue_cache(issue_cache_data):
                    inserted += 1
                else:
                    print(f"[ERROR] Failed to save issue cache for {issue['title']}")
                    skipped += 1
            print(f"[INFO] Successfully saved {inserted} issues to database, skipped {skipped}")
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
        """แปลงและบันทึกข้อมูลกิจกรรมรายวัน (commits, issues, MRs)"""
        try:
            daily_activity = report_data.get('daily_activity', {})
            all_issues = report_data.get('all_issues', [])
            all_mrs = report_data.get('all_merge_requests', [])  # ถ้าไม่มี MR ให้เป็น []

            for date_str, commits in daily_activity.items():
                # Aggregate issues
                issues_created = sum(1 for i in all_issues if i.get('created_at', '').startswith(date_str))
                issues_closed = sum(1 for i in all_issues if i.get('closed_at', '') and i['closed_at'].startswith(date_str))
                
                # Aggregate merge requests (ถ้ามีข้อมูล MR)
                mrs_created = sum(1 for mr in all_mrs if mr.get('created_at', '').startswith(date_str))
                mrs_merged = sum(1 for mr in all_mrs if mr.get('merged_at', '') and mr['merged_at'].startswith(date_str))

                activity_data = {
                    'date': date_str,
                    'commits': commits,
                    'issues_created': issues_created,
                    'issues_closed': issues_closed,
                    'mrs_created': mrs_created,
                    'mrs_merged': mrs_merged
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
    
    def transform_and_save_user_project_activity(self, report_data: Dict[str, Any]) -> bool:
        """แปลงและบันทึกข้อมูล activity แยกตาม user และ project รายวัน"""
        try:
            user_project_activity = report_data.get('user_project_activity', [])
            print(f"[DEBUG] transform_and_save_user_project_activity: count = {len(user_project_activity)}")
            for row in user_project_activity[:3]:
                print("[DEBUG] sample user_project_activity row:", row)
            for row in user_project_activity:
                if not self.db.insert_user_project_activity(row):
                    print(f"[ERROR] Failed to save user_project_activity_cache for {row}")
                    return False
            print(f"[INFO] Successfully saved {len(user_project_activity)} user-project activities to database")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to transform and save user_project_activity_cache: {e}")
            traceback.print_exc()
            return False

    def prepare_user_project_activity(self, report_data: Dict[str, Any]):
        """
        Aggregate activity แยกตาม user, project, date และใส่ลง report_data['user_project_activity']
        ถ้า mapping user_id ไม่เจอ ให้ insert user_id=NULL และ log เหตุผล
        """
        print("[DEBUG] prepare_user_project_activity: all_commits sample:", report_data.get('all_commits', [])[:3])
        print("[DEBUG] prepare_user_project_activity: all_issues sample:", report_data.get('all_issues', [])[:3])
        print("[DEBUG] prepare_user_project_activity: all_merge_requests sample:", report_data.get('all_merge_requests', [])[:3])
        user_project_mappings = report_data.get('user_project_mappings', {})
        all_users = report_data.get('all_users', {})
        from collections import defaultdict
        
        # --- Normalization and mapping logic ---
        def normalize_string(s):
            if not s:
                return ""
            return ' '.join(s.lower().strip().split())
        
        email_to_userid = {}
        name_to_userid = {}
        # Build mapping dicts
        for user in all_users:
            email = normalize_string(user.get('email'))
            name = normalize_string(user.get('name'))
            user_id = user.get('id')
            if email:
                email_to_userid[email] = user_id
            if name:
                name_to_userid[name] = user_id
        # Optional: special mapping (add as needed)
        special_mapping = {
            # "jirapat.ka@tcc-technology.com": 123,
            # "tonjk": 123,
            # "jirapat kaewsongsang": 123,
        }
        def map_user_id(author_name, author_email):
            email = normalize_string(author_email)
            name = normalize_string(author_name)
            if email in special_mapping:
                return special_mapping[email]
            if name in special_mapping:
                return special_mapping[name]
            if email in email_to_userid:
                return email_to_userid[email]
            if name in name_to_userid:
                return name_to_userid[name]
            return None
        # --- End normalization logic ---
        
        activity_map = defaultdict(lambda: {"commits": 0, "issues_created": 0, "issues_closed": 0, "mrs_created": 0, "mrs_merged": 0})
        # Aggregate commits
        for commit in report_data.get('all_commits', []):
            project_id = commit.get('project_id')
            author_name = commit.get('author_name')
            author_email = commit.get('author_email')
            user_id = map_user_id(author_name, author_email)
            if user_id is None:
                print(f"[INFO] Commit by {author_name} ({author_email}) has no user_id mapping, will insert with user_id=NULL")
            date = commit.get('created_at')
            if date:
                date_str = str(datetime.fromisoformat(date.replace('Z', '+00:00')).date())
                key = (project_id, user_id, date_str)
                activity_map[key]["commits"] += 1
        # Aggregate issues
        for issue in report_data.get('all_issues', []):
            project_id = issue.get('project_id')
            assignee_name = issue.get('assignee', {}).get('name') if issue.get('assignee') else None
            assignee_email = issue.get('assignee', {}).get('email') if issue.get('assignee') else None
            user_id = map_user_id(assignee_name, assignee_email)
            if user_id is None:
                print(f"[INFO] Issue assigned to {assignee_name} ({assignee_email}) has no user_id mapping, will insert with user_id=NULL")
            # Created
            if issue.get('created_at'):
                created_date = datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')).date()
                date_str = str(created_date)
                key = (project_id, user_id, date_str)
                activity_map[key]["issues_created"] += 1
            # Closed
            if issue.get('closed_at'):
                closed_date = datetime.fromisoformat(issue['closed_at'].replace('Z', '+00:00')).date()
                date_str = str(closed_date)
                key = (project_id, user_id, date_str)
                activity_map[key]["issues_closed"] += 1
        # Aggregate merge requests
        for project in report_data.get('projects', []):
            project_id = project['id']
            merge_requests = project.get('merge_requests', [])
            for mr in merge_requests:
                author_name = mr.get('author', {}).get('name') if mr.get('author') else None
                author_email = mr.get('author', {}).get('email') if mr.get('author') else None
                user_id = map_user_id(author_name, author_email)
                if user_id is None:
                    print(f"[INFO] MR by {author_name} ({author_email}) has no user_id mapping, will insert with user_id=NULL")
                # Created
                if mr.get('created_at'):
                    created_date = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00')).date()
                    date_str = str(created_date)
                    key = (project_id, user_id, date_str)
                    activity_map[key]["mrs_created"] += 1
                # Merged
                if mr.get('merged_at'):
                    merged_date = datetime.fromisoformat(mr['merged_at'].replace('Z', '+00:00')).date()
                    date_str = str(merged_date)
                    key = (project_id, user_id, date_str)
                    activity_map[key]["mrs_merged"] += 1
        user_project_activity = []
        for (project_id, user_id, date), vals in activity_map.items():
            user_project_activity.append({
                "project_id": project_id,
                "user_id": user_id,  # can be None
                "date": date,
                "commits": vals["commits"],
                "issues_created": vals["issues_created"],
                "issues_closed": vals["issues_closed"],
                "mrs_created": vals["mrs_created"],
                "mrs_merged": vals["mrs_merged"],
                "last_updated": datetime.now(timezone.utc)
            })
        print("[DEBUG] prepare_user_project_activity: user_project_activity sample:", user_project_activity[:3])
        print("[DEBUG] prepare_user_project_activity: user_project_activity count:", len(user_project_activity))
        report_data["user_project_activity"] = user_project_activity

    def transform_and_save_contributor_code_churn(self, report_data: Dict[str, Any], days: int = 30) -> bool:
        """บันทึกข้อมูล contributor code churn ลงฐานข้อมูล"""
        try:
            contributors_detail = report_data.get('contributors_detail', [])
            period_end = datetime.now(timezone.utc)
            period_start = period_end - timedelta(days=days)
            count = 0
            for c in contributors_detail:
                for proj in c.get('projects', []):
                    churn_data = {
                        'contributor_name': c['name'],
                        'contributor_email': c.get('email'),
                        'project_id': proj['project_id'],
                        'project_name': proj['project_name'],
                        'additions': proj['additions'],
                        'deletions': proj['deletions'],
                        'changes': proj['changes'],
                        'period_start': period_start,
                        'period_end': period_end,
                        'period': days,  # <--- เพิ่มตรงนี้
                        'created_at': period_end
                    }
                    if not self.db.insert_contributor_code_churn(churn_data):
                        print(f"[ERROR] Failed to save contributor_code_churn for {c['name']} {proj['project_name']}")
                        return False
                    count += 1
            print(f"[INFO] Successfully saved {count} contributor_code_churn records to database")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to transform and save contributor_code_churn: {e}")
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
            
            # หลังจากบันทึก projects และ members แล้ว
            # ดึง project_id ที่มีอยู่จริงใน DB
            existing_projects = set()
            for row in self.db.execute_query('SELECT id FROM "gitlab-activity-analysis-schema".project_cache') or []:
                existing_projects.add(row['id'])
            # ดึง member_id ที่มีอยู่จริงใน DB
            existing_members = set()
            for row in self.db.execute_query('SELECT id FROM "gitlab-activity-analysis-schema".team_member_cache') or []:
                existing_members.add(row['id'])
            # filter mapping
            valid_mappings = [
                m for m in report_data.get('user_project_mappings', [])
                if m['project_id'] in existing_projects and m['user_id'] in existing_members
            ]
            for m in valid_mappings:
                self.db.upsert_team_member_project(m['user_id'], m['project_id'])
            
            if not self.transform_and_save_issues(report_data):
                return False
            
            if not self.transform_and_save_kpi(report_data):
                return False
            
            if not self.transform_and_save_activity(report_data):
                return False
            
            # เตรียม user_project_activity ก่อน save
            self.prepare_user_project_activity(report_data)
            print("[DEBUG] save_all_data: user_project_activity count:", len(report_data.get('user_project_activity', [])))
            if not self.transform_and_save_user_project_activity(report_data):
                return False
            
            # --- save contributor_code_churn ---
            if not self.transform_and_save_contributor_code_churn(report_data, days=30):
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