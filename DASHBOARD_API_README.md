# GitLab Dashboard API

API สำหรับส่งข้อมูล dashboard ไปยัง frontend applications

## การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements-api.txt
```

### 2. ตั้งค่า Environment Variables

สร้างไฟล์ `.env`:

```env
GITLAB_URL=https://git.lab.tcctech.app
GITLAB_TOKEN=your_gitlab_token_here
DASHBOARD_API_PORT=5000
DASHBOARD_API_DEBUG=false
```

### 3. รัน API Server

```bash
python src/api/dashboard_api.py
```

API จะรันที่ `http://localhost:5000`

## API Endpoints

### 1. Health Check
```http
GET /api/health
```

### 2. Complete Dashboard Data
```http
GET /api/dashboard/data?groups=1721,1267,1269&days=30&team_name=Development Team
```

### 3. Summary Data Only
```http
GET /api/dashboard/summary?groups=1721,1267,1269&days=30
```

### 4. Projects Data Only
```http
GET /api/dashboard/projects?groups=1721,1267,1269&days=30
```

### 5. Issues Data Only
```http
GET /api/dashboard/issues?groups=1721,1267,1269&days=30
```

### 6. Team Data Only
```http
GET /api/dashboard/team?groups=1721,1267,1269&days=30
```

### 7. Clear Cache
```http
POST /api/cache/clear
```

### 8. Get Configuration
```http
GET /api/config
```

## การใช้งานกับ Frontend

### 1. TypeScript Types

ใช้ไฟล์ `frontend/types/dashboard.ts` สำหรับ type definitions

### 2. API Client

ใช้ไฟล์ `frontend/services/api-client.ts` สำหรับการเรียก API

### 3. React Component Example

```tsx
import { Dashboard } from './components/Dashboard';

function App() {
  return (
    <Dashboard 
      groups="1721,1267,1269" 
      days={30} 
      teamName="AI Development Team" 
    />
  );
}
```

## ตัวอย่างการเรียก API

### JavaScript/TypeScript

```typescript
import { apiClient } from './services/api-client';

// Get complete dashboard data
const dashboardData = await apiClient.getDashboardData({
  groups: '1721,1267,1269',
  days: 30,
  team_name: 'Development Team'
});

// Get summary only
const summary = await apiClient.getSummary({
  groups: '1721,1267,1269',
  days: 30
});

// Get projects data
const projects = await apiClient.getProjects({
  groups: '1721,1267,1269',
  days: 30
});
```

### cURL

```bash
# Get complete dashboard data
curl "http://localhost:5000/api/dashboard/data?groups=1721,1267,1269&days=30"

# Get summary only
curl "http://localhost:5000/api/dashboard/summary?groups=1721,1267,1269&days=30"

# Clear cache
curl -X POST "http://localhost:5000/api/cache/clear"
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "data": {
    "metadata": { ... },
    "summary": { ... },
    "projects": [ ... ],
    "groups": { ... },
    "contributors": { ... },
    "daily_activity": { ... },
    "technology_stack": { ... },
    "issue_analytics": { ... },
    "ai_recommendations": [ ... ],
    "team_analytics": { ... },
    "all_issues": [ ... ],
    "api_metadata": { ... }
  },
  "cached": false,
  "timestamp": "2024-01-15T10:30:00"
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description"
}
```

## Caching

- ข้อมูลจะถูก cache เป็นเวลา 5 นาที
- ใช้ endpoint `/api/cache/clear` เพื่อล้าง cache
- Response จะมี field `cached` เพื่อบอกว่าข้อมูลมาจาก cache หรือไม่

## Error Handling

- ตรวจสอบ `response.status` ก่อนใช้งานข้อมูล
- ใช้ `response.message` สำหรับ error details
- HTTP status codes: 200 (success), 400 (bad request), 500 (server error)

## Development

### Debug Mode
```bash
DASHBOARD_API_DEBUG=true python src/api/dashboard_api.py
```

### Custom Port
```bash
DASHBOARD_API_PORT=8080 python src/api/dashboard_api.py
```

## Security

- ใช้ CORS สำหรับ frontend access
- ตรวจสอบ GitLab token ใน environment variables
- ไม่ควร expose API ไปยัง public network โดยไม่มีการ authentication เพิ่มเติม

## Performance

- ใช้ caching เพื่อลดการเรียก GitLab API
- แยก endpoints ตามข้อมูลที่ต้องการ
- ใช้ pagination สำหรับข้อมูลจำนวนมาก (ในอนาคต) 