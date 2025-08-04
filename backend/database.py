import psycopg2
import psycopg2.extras
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, date, timedelta
import json
import os
from dotenv import load_dotenv
import traceback

bkk_timezone = timezone(timedelta(hours=7))

load_dotenv(dotenv_path='E:/TCC/gitlab_activity/gitlab-activity-analysis/.env')

def convert_datetime_for_json(obj):
    """Convert datetime objects to ISO format strings for JSON serialization"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetime_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_for_json(item) for item in obj]
    else:
        return obj

class DatabaseManager:
    """จัดการการเชื่อมต่อและดำเนินการกับฐานข้อมูล PostgreSQL"""
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        if db_config is None:
            db_config = {
                'dbname': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT'))
            }
            if not db_config['dbname']:
                raise ValueError("DB_NAME environment variable is required")
            if not db_config['user']:
                raise ValueError("DB_USER environment variable is required")
            if not db_config['password']:
                print("[WARNING] DB_PASSWORD not set - using empty password")
            try:
                db_config['port'] = int(db_config['port'])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid DB_PORT: {os.getenv('DB_PORT')}. Must be a number.")
        self.db_config = db_config
        self.connection = None
    
    def connect(self):
        # try:
        self.connection = psycopg2.connect(**self.db_config)
        print(f"[INFO] Connected to database: {self.db_config['dbname']}")
        return True
        # except Exception as e:
        #     print(f"[ERROR] Failed to connect to database: {e}")
        #     return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            print("[INFO] Database connection closed")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[List[Dict]]:
        if not self.connection:
            print("[ERROR] No database connection")
            return None
        # try:
        with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return True
        # except Exception as e:
        #     print(f"[ERROR] Query execution failed: {e}")
        #     print(f"[ERROR] Query: {query}")
        #     print(f"[ERROR] Params: {params}")
        #     traceback.print_exc()
        #     self.connection.rollback()
        #     return None

    def upsert_group_cache(self, group_data: Dict[str, Any]) -> bool:
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
            group_data['active_users'],
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S')
        )
        result = self.execute_query(query, params)
        return result is True

    def upsert_project_cache(self, project_data: Dict[str, Any]) -> bool:
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
        last_activity = None
        if project_data.get('last_activity_at'):
            # try:
            last_activity = datetime.fromisoformat(
                project_data['last_activity_at'].replace('Z', '+00:00')
            )
            last_activity = last_activity.astimezone(bkk_timezone)
            # except:
            #     pass
        elif project_data.get('last_activity'):
            # try:
            last_activity = datetime.fromisoformat(
                project_data['last_activity'].replace('Z', '+00:00')
            )
            last_activity = last_activity.astimezone(bkk_timezone)
            # except:
            #     pass
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
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S')
        )
        result = self.execute_query(query, params)
        return result is True

    def upsert_team_member_cache(self, member_data: Dict[str, Any]) -> bool:
        last_activity = None
        if member_data.get('last_activity'):
            # try:
            last_activity = datetime.fromisoformat(
                member_data['last_activity'].replace('Z', '+00:00')
            )
            # except:
            #     pass
        email = member_data.get('email')
        if email:
            email = email.lower()
        username = member_data.get('username')
        if not username and email:
            username = email.split('@')[0]
        elif not username:
            name = member_data.get('name', 'unknown_user')
            username = name.lower().replace(' ', '_').replace('.', '')
        columns = [
            "id", "gitlab_user_id", "name", "email", "username", "commits", "issues_assigned",
            "issues_resolved", "merge_requests", "last_activity", "last_updated"
        ]
        values = [
            member_data['id'],
            member_data.get('gitlab_user_id'),
            member_data.get('name', 'Unknown User'),
            email,
            username,
            member_data.get('commits', 0),
            member_data.get('issues_assigned', 0),
            member_data.get('issues_resolved', 0),
            member_data.get('merge_requests', 0),
            last_activity,
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S')
        ]
        query = f'''
        INSERT INTO "gitlab-activity-analysis-schema".team_member_cache (
            {', '.join(columns)}
        ) VALUES ({', '.join(['%s'] * len(values))})
        ON CONFLICT (id) DO UPDATE SET
            gitlab_user_id = EXCLUDED.gitlab_user_id,
            name = EXCLUDED.name,
            username = EXCLUDED.username,
            commits = EXCLUDED.commits,
            issues_assigned = EXCLUDED.issues_assigned,
            issues_resolved = EXCLUDED.issues_resolved,
            merge_requests = EXCLUDED.merge_requests,
            last_activity = EXCLUDED.last_activity,
            last_updated = EXCLUDED.last_updated,
            email = COALESCE(EXCLUDED.email, "gitlab-activity-analysis-schema".team_member_cache.email)
        '''
        result = self.execute_query(query, tuple(values))
        return result is True

    def upsert_team_member_project(self, member_id: int, project_id: int) -> bool:
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".team_member_project (member_id, project_id)
        VALUES (%s, %s)
        ON CONFLICT (member_id, project_id) DO NOTHING
        """
        return self.execute_query(query, (member_id, project_id)) is not None

    def upsert_issue_cache(self, issue_data: Dict[str, Any]) -> bool:
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
        created_at = None
        updated_at = None
        closed_at = None
        due_date = None
        # try:
        if issue_data.get('created_at'):
            created_at = datetime.fromisoformat(
                issue_data['created_at'].replace('Z', '+00:00')
            )
            created_at = created_at.astimezone(bkk_timezone)
        if issue_data.get('updated_at'):
            updated_at = datetime.fromisoformat(
                issue_data['updated_at'].replace('Z', '+00:00')
            )
            updated_at = updated_at.astimezone(bkk_timezone)
        if issue_data.get('closed_at'):
            closed_at = datetime.fromisoformat(
                issue_data['closed_at'].replace('Z', '+00:00')
            )
            closed_at = closed_at.astimezone(bkk_timezone)
        if issue_data.get('due_date'):
            due_date = datetime.fromisoformat(issue_data['due_date']).date()
        # except:
        #     pass
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
            created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else None,
            updated_at.strftime('%Y-%m-%d %H:%M:%S') if updated_at else None,
            closed_at.strftime('%Y-%m-%d %H:%M:%S') if closed_at else None,
            due_date if due_date else None,
            issue_data.get('labels', []),
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S')
        )
        return self.execute_query(query, params) is not None

    def upsert_kpi_cache(self, kpi_data: Dict[str, Any]) -> bool:
        delete_query = """
        DELETE FROM "gitlab-activity-analysis-schema".kpi_cache
        """
        self.execute_query(delete_query)
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
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S'),
            kpi_data.get('period', '30d')
        )
        result = self.execute_query(query, params)
        return result is True

    def upsert_activity_cache(self, activity_data: Dict[str, Any]) -> bool:
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
            datetime.now(bkk_timezone).strftime('%Y-%m-%d %H:%M:%S')
        )
        return self.execute_query(query, params) is not None

    def insert_contributor_code_churn(self, churn_data: dict) -> bool:
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'gitlab-activity-analysis-schema' 
            AND table_name = 'contributor_code_churn'
        );
        """
        table_exists = self.execute_query(check_table_query)
        if not table_exists or not table_exists[0]['exists']:
            print("[WARNING] Table contributor_code_churn does not exist. Skipping code churn data.")
            return True
        query = '''
        INSERT INTO "gitlab-activity-analysis-schema".contributor_code_churn (
            contributor_name, contributor_email, project_id, project_name,
            additions, deletions, changes, period_start, period_end, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        period_start = None
        period_end = None
        created_at = None
        # try:
        if churn_data.get('period_start'):
            if isinstance(churn_data['period_start'], datetime):
                period_start = churn_data['period_start'].replace(tzinfo=None)
            else:
                period_start = datetime.fromisoformat(str(churn_data['period_start']).replace('Z', '')).replace(tzinfo=None)
        if churn_data.get('period_end'):
            if isinstance(churn_data['period_end'], datetime):
                period_end = churn_data['period_end'].replace(tzinfo=None)
            else:
                period_end = datetime.fromisoformat(str(churn_data['period_end']).replace('Z', '')).replace(tzinfo=None)
        if churn_data.get('created_at'):
            if isinstance(churn_data['created_at'], datetime):
                created_at = churn_data['created_at'].replace(tzinfo=None)
            else:
                created_at = datetime.fromisoformat(str(churn_data['created_at']).replace('Z', '')).replace(tzinfo=None)
        else:
            created_at = datetime.now().replace(tzinfo=None)
        # except Exception as e:
            # print(f"[WARNING] Failed to parse timestamps for code churn data: {e}")
        now = datetime.now().replace(tzinfo=None)
        period_start = period_start or now
        period_end = period_end or now
        created_at = created_at or now
        params = (
            churn_data['contributor_name'],
            churn_data.get('contributor_email'),
            churn_data['project_id'],
            churn_data['project_name'],
            churn_data['additions'],
            churn_data['deletions'],
            churn_data['changes'],
            period_start.strftime('%Y-%m-%d %H:%M:%S'),
            period_end.strftime('%Y-%m-%d %H:%M:%S'),
            created_at.strftime('%Y-%m-%d %H:%M:%S')
        )
        return self.execute_query(query, params) is not None

    def insert_user_project_activity(self, data: dict) -> bool:
        user_id = data.get('user_id')
        if user_id is None:
            print(f"[WARNING] Skipping user_project_activity_cache entry with NULL user_id for project {data.get('project_id')}")
            return True
        check_user_query = """
        SELECT id FROM "gitlab-activity-analysis-schema".team_member_cache WHERE id = %s
        """
        user_exists = self.execute_query(check_user_query, (user_id,))
        if not user_exists:
            print(f"[WARNING] User ID {user_id} not found in team_member_cache. Skipping entry.")
            return True
        query = """
        INSERT INTO "gitlab-activity-analysis-schema".user_project_activity_cache (
            project_id, user_id, date, commits, issues_created, issues_closed,
            mrs_created, mrs_merged, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        last_updated = data.get('last_updated')
        if last_updated is None:
            last_updated = datetime.now(bkk_timezone)
        params = (
            data['project_id'],
            user_id,
            data['date'],
            data.get('commits', 0),
            data.get('issues_created', 0),
            data.get('issues_closed', 0),
            data.get('mrs_created', 0),
            data.get('mrs_merged', 0),
            last_updated.strftime('%Y-%m-%d %H:%M:%S')
        )
        # try:
        self.execute_query(query, params)
        return True
        # except Exception as e:
        #     print(f"[ERROR] insert_user_project_activity: {e}")
        #     traceback.print_exc()
        #     return False

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
        serializable_data = convert_datetime_for_json(data)
        params = (
            cache_id,
            data_type,
            json.dumps(serializable_data),
            source,
            now.strftime('%Y-%m-%d %H:%M:%S'),
            now.strftime('%Y-%m-%d %H:%M:%S'),
            expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else None,
            json.dumps({})
        )
        return self.execute_query(query, params) is not None

 