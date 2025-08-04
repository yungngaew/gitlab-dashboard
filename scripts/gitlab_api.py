import requests
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timezone

# ฟังก์ชันโหลด contributor mapping
def build_contributor_mapping() -> Tuple[Dict[str, str], Dict[str, str]]:
    mapping = {}
    email_mapping = {}
    known_mappings = {
        'ta.khongsap@gmail.com': 'Totrakool Khongsap',
        'tkhongsap': 'Totrakool Khongsap',
        'i1032745@THAIBEV.COM': 'Totrakool Khongsap',
        'totrakool.k@thaibev.com': 'Totrakool Khongsap'
    }
    for key, canonical in known_mappings.items():
        if '@' in key:
            email_mapping[key.lower()] = canonical
        else:
            mapping[key.lower()] = canonical
    return mapping, email_mapping

# ฟังก์ชัน normalize contributor name
def normalize_contributor_name(name: str, email: str = '', name_mapping: Optional[Dict[str, str]] = None, email_mapping: Optional[Dict[str, str]] = None) -> str:
    if name_mapping is None or email_mapping is None:
        name_mapping, email_mapping = build_contributor_mapping()
    
    # First check email-based mapping (most reliable)
    if email:
        email_lower = email.lower()
        if email_lower in email_mapping:
            return email_mapping[email_lower]
    
    # Check explicit name mapping
    if name in name_mapping:
        return name_mapping[name]
    
    # Check case-insensitive name mapping
    name_lower = name.lower()
    if name_lower in name_mapping:
        return name_mapping[name_lower]
    
    # Try to match by email domain patterns
    if email:
        # Extract username from email
        email_username = email.split('@')[0]
        if email_username in name_mapping:
            return name_mapping[email_username]
        
        # Simple heuristics for common patterns
        email_lower = email.lower()
        name_lower = name.lower()
        
        # If email starts with name, they're likely the same person
        if email_lower.startswith(name_lower.replace(' ', '.')):
            return name
        if email_lower.startswith(name_lower.replace(' ', '')):
            return name
    
    return name

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
        if not any(key in endpoint for key in ['groups', 'projects', 'commits', 'merge_requests', 'issues']):
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