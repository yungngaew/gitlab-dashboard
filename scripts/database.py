import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import os
from dotenv import load_dotenv
import traceback

load_dotenv(dotenv_path='E:/TCC/gitlab_activity/gitlab-activity-analysis/.env')

class DatabaseManager:
    """จัดการการเชื่อมต่อและดำเนินการกับฐานข้อมูล PostgreSQL"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """Initialize database connection"""
        if db_config is None:
            # ใช้ environment variables พร้อม default values
            db_config = {
                'dbname': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT'))
            }
            
            # Validate required fields
            if not db_config['dbname']:
                raise ValueError("DB_NAME environment variable is required")
            if not db_config['user']:
                raise ValueError("DB_USER environment variable is required")
            if not db_config['password']:
                print("[WARNING] DB_PASSWORD not set - using empty password")
            
            # Validate port number
            try:
                db_config['port'] = int(db_config['port'])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid DB_PORT: {os.getenv('DB_PORT')}. Must be a number.")
        
        self.db_config = db_config
        self.connection = None
    
    def connect(self):
        """เชื่อมต่อกับฐานข้อมูล"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            print(f"[INFO] Connected to database: {self.db_config['dbname']}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """ปิดการเชื่อมต่อฐานข้อมูล"""
        if self.connection:
            self.connection.close()
            print("[INFO] Database connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[List[Dict]]:
        """Execute query และ return results"""
        if not self.connection:
            print("[ERROR] No database connection")
            return None
        
        try:
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return True  # Return True for successful INSERT/UPDATE/DELETE
        except Exception as e:
            print(f"[ERROR] Query execution failed: {e}")
            print(f"[ERROR] Query: {query}")
            print(f"[ERROR] Params: {params}")
            traceback.print_exc()
            self.connection.rollback()
            return None
    
    def upsert_group_cache(self, group_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน group_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".group_cache (
            id, name, path, health_grade, total_commits, 
            total_issues, total_mrs, active_users, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path,
            health_grade = EXCLUDED.health_grade,
            total_commits = EXCLUDED.total_commits,
            total_issues = EXCLUDED.total_issues,
            total_mrs = EXCLUDED.total_mrs,
            active_users = EXCLUDED.active_users,
            last_updated = EXCLUDED.last_updated
        """
        
        params = (
            group_data['id'],
            group_data['name'],
            group_data['path'],
            group_data['health_grade'],
            group_data['total_commits'],
            group_data['total_issues'],
            group_data['total_mrs'],
            group_data['active_users'],  # ใช้ active_users จาก group_cache_data
            datetime.now(timezone.utc)
        )
        
        result = self.execute_query(query, params)
        return result is True
    
    def upsert_project_cache(self, project_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน project_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".project_cache (
            id, name, name_with_namespace, path_with_namespace, description,
            status, health_grade, open_issues, mrs_created, commits_30d,
            contributors_30d, last_activity, group_id, group_name, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            name_with_namespace = EXCLUDED.name_with_namespace,
            path_with_namespace = EXCLUDED.path_with_namespace,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            health_grade = EXCLUDED.health_grade,
            open_issues = EXCLUDED.open_issues,
            mrs_created = EXCLUDED.mrs_created,
            commits_30d = EXCLUDED.commits_30d,
            contributors_30d = EXCLUDED.contributors_30d,
            last_activity = EXCLUDED.last_activity,
            group_id = EXCLUDED.group_id,
            group_name = EXCLUDED.group_name,
            last_updated = EXCLUDED.last_updated
        """
        
        # Parse last_activity timestamp
        last_activity = None
        if project_data.get('last_activity'):
            try:
                last_activity = datetime.fromisoformat(
                    project_data['last_activity'].replace('Z', '+00:00')
                )
            except:
                pass
        
        params = (
            project_data['id'],
            project_data['name'],
            project_data.get('name_with_namespace', project_data['name']),
            project_data.get('path_with_namespace', project_data.get('path', '')),
            project_data.get('description', ''),
            project_data.get('status', 'active'),
            project_data.get('health_grade', 'D'),
            project_data.get('open_issues', 0),
            project_data.get('mrs_created', 0),
            project_data.get('commits_30d', 0),
            project_data.get('contributors_30d', 0),
            last_activity,
            project_data.get('group_id'),
            project_data.get('group_name', ''),
            datetime.now(timezone.utc)
        )
        
        result = self.execute_query(query, params)
        return result is True
    
    def upsert_team_member_cache(self, member_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน team_member_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".team_member_cache (
            id, name, email, username, commits, issues_assigned,
            issues_resolved, merge_requests, last_activity, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET
            name = EXCLUDED.name,
            username = EXCLUDED.username,
            commits = EXCLUDED.commits,
            issues_assigned = EXCLUDED.issues_assigned,
            issues_resolved = EXCLUDED.issues_resolved,
            merge_requests = EXCLUDED.merge_requests,
            last_activity = EXCLUDED.last_activity,
            last_updated = EXCLUDED.last_updated
        """
        
        # Parse last_activity timestamp
        last_activity = None
        if member_data.get('last_activity'):
            try:
                last_activity = datetime.fromisoformat(
                    member_data['last_activity'].replace('Z', '+00:00')
                )
            except:
                pass
        
        params = (
            member_data.get('id', hash(member_data['email']) % 2147483647),  # Generate ID from email
            member_data['name'],
            member_data['email'],
            member_data.get('username', member_data['email'].split('@')[0]),
            member_data.get('commits', 0),
            member_data.get('issues_assigned', 0),
            member_data.get('issues_resolved', 0),
            member_data.get('merge_requests', 0),
            last_activity,
            datetime.now(timezone.utc)
        )
        
        result = self.execute_query(query, params)
        return result is True
    
    def upsert_team_member_project(self, member_id: int, project_id: int) -> bool:
        """Insert ข้อมูลใน team_member_project (many-to-many relationship)"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".team_member_project (member_id, project_id)
        VALUES (%s, %s)
        ON CONFLICT (member_id, project_id) DO NOTHING
        """
        
        return self.execute_query(query, (member_id, project_id)) is not None
    
    def upsert_issue_cache(self, issue_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน issue_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".issue_cache (
            id, iid, project_id, project_name, title, description,
            state, priority, assignee_email, assignee_name, author_name,
            created_at, updated_at, closed_at, due_date, labels, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            iid = EXCLUDED.iid,
            project_id = EXCLUDED.project_id,
            project_name = EXCLUDED.project_name,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            state = EXCLUDED.state,
            priority = EXCLUDED.priority,
            assignee_email = EXCLUDED.assignee_email,
            assignee_name = EXCLUDED.assignee_name,
            author_name = EXCLUDED.author_name,
            created_at = EXCLUDED.created_at,
            updated_at = EXCLUDED.updated_at,
            closed_at = EXCLUDED.closed_at,
            due_date = EXCLUDED.due_date,
            labels = EXCLUDED.labels,
            last_updated = EXCLUDED.last_updated
        """
        
        # Parse timestamps
        created_at = None
        updated_at = None
        closed_at = None
        due_date = None
        
        try:
            if issue_data.get('created_at'):
                created_at = datetime.fromisoformat(
                    issue_data['created_at'].replace('Z', '+00:00')
                )
            if issue_data.get('updated_at'):
                updated_at = datetime.fromisoformat(
                    issue_data['updated_at'].replace('Z', '+00:00')
                )
            if issue_data.get('closed_at'):
                closed_at = datetime.fromisoformat(
                    issue_data['closed_at'].replace('Z', '+00:00')
                )
            if issue_data.get('due_date'):
                due_date = datetime.fromisoformat(issue_data['due_date']).date()
        except:
            pass
        
        params = (
            issue_data['id'],
            issue_data.get('iid', issue_data['id']),
            issue_data['project_id'],
            issue_data['project_name'],
            issue_data['title'],
            issue_data.get('description', ''),
            issue_data.get('state', 'opened'),
            issue_data.get('priority', 'medium'),
            issue_data.get('assignee_email'),
            issue_data.get('assignee_name', ''),
            issue_data.get('author_name', ''),
            created_at,
            updated_at,
            closed_at,
            due_date,
            issue_data.get('labels', []),
            datetime.now(timezone.utc)
        )
        
        return self.execute_query(query, params) is not None
    
    def upsert_kpi_cache(self, kpi_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน kpi_cache"""
        # ลบข้อมูลเก่าก่อน (ถ้ามี)
        delete_query = """
        DELETE FROM "gitlab-activity-analysis-schema".kpi_cache 
        WHERE period = %s
        """
        self.execute_query(delete_query, (kpi_data.get('period', '30d'),))
        
        # เพิ่มข้อมูลใหม่
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".kpi_cache (
            total_commits, total_mrs, total_issues, active_projects,
            last_updated, period
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        params = (
            kpi_data.get('total_commits', 0),
            kpi_data.get('total_mrs', 0),
            kpi_data.get('total_issues', 0),
            kpi_data.get('active_projects', 0),
            datetime.now(timezone.utc),
            kpi_data.get('period', '30d')
        )
        
        result = self.execute_query(query, params)
        return result is True
    
    def upsert_activity_cache(self, activity_data: Dict[str, Any]) -> bool:
        """Insert หรือ Update ข้อมูลใน activity_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".activity_cache (
            date, commits, issues_created, issues_closed,
            mrs_created, mrs_merged, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            commits = EXCLUDED.commits,
            issues_created = EXCLUDED.issues_created,
            issues_closed = EXCLUDED.issues_closed,
            mrs_created = EXCLUDED.mrs_created,
            mrs_merged = EXCLUDED.mrs_merged,
            last_updated = EXCLUDED.last_updated
        """
        
        params = (
            activity_data['date'],
            activity_data.get('commits', 0),
            activity_data.get('issues_created', 0),
            activity_data.get('issues_closed', 0),
            activity_data.get('mrs_created', 0),
            activity_data.get('mrs_merged', 0),
            datetime.now(timezone.utc)
        )
        
        return self.execute_query(query, params) is not None
    
    def upsert_dashboard_cache(self, cache_id: str, data_type: str, data: Dict[str, Any], 
                              source: str = 'gitlab_api', expires_at: Optional[datetime] = None) -> bool:
        """Insert หรือ Update ข้อมูลใน dashboard_cache"""
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".dashboard_cache (
            id, data_type, data, source, created_at, updated_at, expires_at, metadata
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            data_type = EXCLUDED.data_type,
            data = EXCLUDED.data,
            source = EXCLUDED.source,
            updated_at = EXCLUDED.updated_at,
            expires_at = EXCLUDED.expires_at,
            metadata = EXCLUDED.metadata
        """
        
        now = datetime.now(timezone.utc)
        
        params = (
            cache_id,
            data_type,
            json.dumps(data),
            source,
            now,
            now,
            expires_at,
            json.dumps({})
        )
        
        return self.execute_query(query, params) is not None
    
    def get_cached_data(self, cache_id: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลจาก dashboard_cache"""
        query = "SELECT data FROM \"gitlab-activity-analysis-schema\".dashboard_cache WHERE id = %s"
        result = self.execute_query(query, (cache_id,))
        
        if result and len(result) > 0:
            return json.loads(result[0]['data'])
        return None
    
    def clear_expired_cache(self) -> bool:
        """ลบ cache ที่หมดอายุแล้ว"""
        query = "DELETE FROM \"gitlab-activity-analysis-schema\".dashboard_cache WHERE expires_at < NOW()"
        return self.execute_query(query) is not None 