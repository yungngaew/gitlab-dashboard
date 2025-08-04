import requests
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timezone


# ฟังก์ชันดึงรายการ group IDs ทั้งหมด
def get_all_group_ids(gitlab_url: str, gitlab_token: str) -> List[int]:
    """Get all group IDs from GitLab."""
    headers = {"Authorization": f"Bearer {gitlab_token}"}
    group_ids = []
    page = 1
    while True:
        resp = requests.get(
            f"{gitlab_url}/api/v4/groups",
            headers=headers,
            params={"per_page": 100, "page": page}
        )
        resp.raise_for_status()
        groups = resp.json()
        if not groups:
            break
        group_ids.extend([g['id'] for g in groups])
        page += 1
    return group_ids

# ฟังก์ชัน request GitLab API แบบพื้นฐาน
def simple_gitlab_request(url: str, token: str, endpoint: str, params: Optional[Dict] = None) -> Any:
    """Make a simple GitLab API request with pagination support."""
    headers = {"Authorization": f"Bearer {token}"}
    full_url = f"{url}/api/v4/{endpoint}"
    
    try:
        request_params = params or {}
        
        # สำหรับ single object (เช่น group info) ไม่ต้องใช้ pagination
        # ตรวจสอบว่าเป็น single object request หรือ list request
        if '/' in endpoint and not endpoint.endswith('/') and not any(key in endpoint for key in ['/projects', '/commits', '/merge_requests', '/issues']):
            # Single object request (เช่น groups/1721, projects/123)
            response = requests.get(full_url, headers=headers, params=request_params)
            response.raise_for_status()
            return response.json()
        
        # สำหรับ list objects ใช้ pagination
        all_results = []
        page = 1
        per_page = 100
        
        while True:
            request_params.update({'page': page, 'per_page': per_page})
            
            response = requests.get(full_url, headers=headers, params=request_params)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                break
                
            all_results.extend(results)
            
            # Check if there are more pages
            if len(results) < per_page:
                break
            page += 1
            
        return all_results
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] GitLab API Error: {e}")
        return []

# ฟังก์ชันตรวจสอบและทำความสะอาดข้อมูล
def validate_and_clean_data(data: Any, data_type: str) -> Any:
    """Validate and clean data from GitLab API responses."""
    if data_type == 'commit':
        required_fields = ['id', 'title', 'created_at', 'author_name']
        if not all(field in data for field in required_fields):
            return None
        
        # Clean author name
        if data.get('author_name'):
            data['author_name'] = data['author_name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
            
    elif data_type == 'merge_request':
        required_fields = ['id', 'title', 'created_at', 'author']
        if not all(field in data for field in required_fields):
            return None
        
        # Validate author structure
        if not isinstance(data.get('author'), dict):
            return None
        
        # Clean author name
        if data['author'].get('name'):
            data['author']['name'] = data['author']['name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
            
    elif data_type == 'issue':
        required_fields = ['id', 'title', 'created_at', 'state']
        if not all(field in data for field in required_fields):
            return None
        
        # Clean assignee if present
        if data.get('assignee') and isinstance(data['assignee'], dict):
            if data['assignee'].get('name'):
                data['assignee']['name'] = data['assignee']['name'].strip()
        
        # Validate date
        try:
            datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    
    return data

# ฟังก์ชัน request GitLab API แบบปลอดภัย
def safe_gitlab_request(url: str, token: str, endpoint: str, params: Optional[Dict] = None, data_type: str = 'generic') -> List[Any]:
    """Make a safe GitLab API request with data validation and error handling."""
    try:
        raw_data = simple_gitlab_request(url, token, endpoint, params)
        
        if not isinstance(raw_data, list):
            print(f"[WARNING] Expected list from {endpoint}, got {type(raw_data)}")
            return []
        
        # Validate and clean each item
        cleaned_data = []
        for item in raw_data:
            if isinstance(item, dict):
                cleaned_item = validate_and_clean_data(item, data_type)
                if cleaned_item:
                    cleaned_data.append(cleaned_item)
        
        print(f"[INFO] Retrieved {len(cleaned_data)} valid {data_type} items from {endpoint}")
        return cleaned_data
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch {data_type} from {endpoint}: {e}")
        return [] 


def fetch_all_users_and_mappings(gitlab_url: str, gitlab_token: str, project_ids: list, since: str, until: str):
    """ดึงข้อมูล user, commit, merge request, และ mapping user-project จาก GitLab API โดยใช้ User ID เป็นหลัก"""
    headers = {"Authorization": f"Bearer {gitlab_token}"}
    
    # --- โครงสร้างข้อมูลใหม่ ---
    all_users = dict()  # Key: user_id (ตัวเลข), Value: ข้อมูล user
    email_to_id_cache = {}
    user_project_mappings = set() # จะเก็บ (user_id, project_id)

    # --- ฟังก์ชันช่วย: ค้นหา User ID จากอีเมล ---
    def get_user_id_from_email(email, name, username=None):
        if not email and not username and not name:
            return None
        # 1. พยายามหา user id จาก email ก่อน
        if email:
            if email in email_to_id_cache:
                return email_to_id_cache[email]
            try:
                resp = requests.get(
                    f"{gitlab_url}/api/v4/users",
                    headers=headers,
                    params={"search": email}
                )
                resp.raise_for_status()
                results = resp.json()
                if results:
                    user_data = results[0]
                    user_id = user_data['id']
                    email_to_id_cache[email] = user_id
                    if user_id not in all_users:
                        all_users[user_id] = {
                            'id': user_id,
                            'name': user_data.get('name', name),
                            'email': email,
                            'username': user_data.get('username'),
                            'commits': 0, 'merge_requests': 0, 'issues_assigned': 0
                        }
                    return user_id
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] API Error when searching for user {email}: {e}")
        # 2. fallback: หา user id จาก username
        if username:
            try:
                resp = requests.get(
                    f"{gitlab_url}/api/v4/users",
                    headers=headers,
                    params={"username": username}
                )
                resp.raise_for_status()
                results = resp.json()
                if results:
                    user_data = results[0]
                    user_id = user_data['id']
                    if user_id not in all_users:
                        all_users[user_id] = {
                            'id': user_id,
                            'name': user_data.get('name', name),
                            'email': user_data.get('email', email),
                            'username': username,
                            'commits': 0, 'merge_requests': 0, 'issues_assigned': 0
                        }
                    return user_id
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] API Error when searching for user by username {username}: {e}")
        # 3. fallback: หา user id จาก name
        if name:
            try:
                resp = requests.get(
                    f"{gitlab_url}/api/v4/users",
                    headers=headers,
                    params={"search": name}
                )
                resp.raise_for_status()
                results = resp.json()
                if results:
                    user_data = results[0]
                    user_id = user_data['id']
                    if user_id not in all_users:
                        all_users[user_id] = {
                            'id': user_id,
                            'name': name,
                            'email': user_data.get('email', email),
                            'username': user_data.get('username'),
                            'commits': 0, 'merge_requests': 0, 'issues_assigned': 0
                        }
                    return user_id
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] API Error when searching for user by name {name}: {e}")
        return None

    # --- เริ่มลูปหลัก ---
    for pid in project_ids:
        # --- 1. ดึง Merge Requests (เพื่อสร้าง Cache) ---
        page = 1
        while True:
            try:
                resp = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/merge_requests", headers=headers, params={"created_after": since, "created_before": until, "per_page": 100, "page": page, "scope": "all"})
                resp.raise_for_status()
                mrs = resp.json()
                if not mrs: break
                
                for mr in mrs:
                    author = mr.get("author", {})
                    author_id = author.get("id")
                    author_email = author.get("email")
                    
                    if author_id:
                        if author_id not in all_users:
                            all_users[author_id] = {'id': author_id, 'name': author.get('name'), 'email': author_email, 'username': author.get('username'), 'commits': 0, 'merge_requests': 0, 'issues_assigned': 0}
                        
                        all_users[author_id]['merge_requests'] += 1
                        user_project_mappings.add((author_id, pid))

                        if author_email:
                            email_to_id_cache[author_email] = author_id

                if len(mrs) < 100: break
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Could not fetch MRs for project {pid}: {e}")
                break

        # --- 2. ดึง Issues (เพื่อสร้าง Cache เพิ่มเติม) ---
        # ดึง opened issues (เดิม)
        page = 1
        while True:
            try:
                resp = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/issues", headers=headers, params={"state": "opened", "per_page": 100, "page": page})
                resp.raise_for_status()
                issues = resp.json()
                if not issues: break

                for issue in issues:
                    assignee = issue.get("assignee")
                    if assignee:
                        assignee_id = assignee.get("id")
                        assignee_email = assignee.get("email")
                        if assignee_id:
                            if assignee_id not in all_users:
                                all_users[assignee_id] = {'id': assignee_id, 'name': assignee.get('name'), 'email': assignee_email, 'username': assignee.get('username'), 'commits': 0, 'merge_requests': 0, 'issues_assigned': 0, 'issues_resolved': 0}
                            all_users[assignee_id]['issues_assigned'] += 1
                            user_project_mappings.add((assignee_id, pid))
                            if assignee_email:
                                email_to_id_cache[assignee_email] = assignee_id
                if len(issues) < 100: break
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Could not fetch Issues for project {pid}: {e}")
                break
        # ดึง closed issues (ใหม่ สำหรับ issues_resolved)
        page = 1
        while True:
            try:
                resp = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/issues", headers=headers, params={"state": "closed", "per_page": 100, "page": page})
                resp.raise_for_status()
                issues = resp.json()
                if not issues: break
                for issue in issues:
                    assignee = issue.get("assignee")
                    if assignee:
                        assignee_id = assignee.get("id")
                        assignee_email = assignee.get("email")
                        if assignee_id:
                            if assignee_id not in all_users:
                                all_users[assignee_id] = {'id': assignee_id, 'name': assignee.get('name'), 'email': assignee_email, 'username': assignee.get('username'), 'commits': 0, 'merge_requests': 0, 'issues_assigned': 0, 'issues_resolved': 0}
                            if 'issues_resolved' not in all_users[assignee_id]:
                                all_users[assignee_id]['issues_resolved'] = 0
                            all_users[assignee_id]['issues_resolved'] += 1
                            user_project_mappings.add((assignee_id, pid))
                            if assignee_email:
                                email_to_id_cache[assignee_email] = assignee_id
                if len(issues) < 100: break
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Could not fetch Closed Issues for project {pid}: {e}")
                break
        
        # --- 3. ดึง Commits (ใช้ Cache และเรียก API เมื่อจำเป็น) ---
        page = 1
        while True:
            try:
                resp = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/repository/commits", headers=headers, params={"since": since, "until": until, "per_page": 100, "page": page})
                resp.raise_for_status()
                commits = resp.json()
                if not commits: break
                
                for c in commits:
                    author_email = c.get("author_email")
                    author_name = c.get("author_name")
                    author_username = c.get("author_name")  # GitLab API ไม่มี author_username ใน commit, อาจต้อง map เพิ่มเองถ้ามี
                    user_id = get_user_id_from_email(author_email, author_name, author_username)
                    if user_id:
                        all_users[user_id]['commits'] += 1
                        user_project_mappings.add((user_id, pid))
                    else:
                        print(f"[INFO] Could not map commit author '{author_name} <{author_email}>' to a user ID (even with fallback).")

                if len(commits) < 100: break
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Could not fetch Commits for project {pid}: {e}")
                break

        # --- 4. ดึง Members (เพื่อสร้าง Cache และ enrich last_activity) ---
        page = 1
        while True:
            try:
                resp = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/members", headers=headers, params={"per_page": 100, "page": page})
                resp.raise_for_status()
                members = resp.json()
                if not members: break

                for member in members:
                    user_id = member.get('id')
                    if user_id and user_id not in all_users:
                        all_users[user_id] = {
                            'id': user_id,
                            'name': member.get('name', ''),
                            'email': member.get('email', ''),
                            'username': member.get('username', ''),
                            'commits': 0, 'merge_requests': 0, 'issues_assigned': 0, 'issues_resolved': 0,
                            'last_activity': member.get('last_activity_on') or member.get('last_sign_in_at') or ''
                        }

                if len(members) < 100: break
                page += 1
            except requests.exceptions.RequestException as e:
                print(f"[WARNING] Could not fetch Members for project {pid}: {e}")
                break

    # --- แปลง mapping เป็น list ---
    user_project_mappings_list = [
        {"user_id": uid, "project_id": pid}
        for (uid, pid) in user_project_mappings
    ]
    
    # แปลง all_users dict เป็น list of dicts
    final_users_list = list(all_users.values())

    return final_users_list, user_project_mappings_list