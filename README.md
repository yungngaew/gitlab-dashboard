# GitLab Tools

*Streamline GitLab management with bulk operations, analytics, and automated reporting*

## Overview

GitLab Tools is a professional-grade suite for managing GitLab at scale. Perfect for teams who need to modernize Git workflows, generate executive dashboards, and automate team productivity reporting.

**Key Benefits:**
- 🔄 **Bulk Branch Renaming** - Safely modernize from trunk/master to main across all repositories
- 📊 **Executive Dashboards** - Automated HTML reports with health scoring and visual analytics  
- 📈 **Team Productivity Reports** - Weekly email reports with contributor insights and metrics
- 🎯 **Bulk Issue Creation** - Convert planning documents to GitLab issues automatically

## 🚀 Quick Start (15 minutes)

### 1. Installation
```bash
# Clone repository
git clone https://github.com/tkhongsap/tcctech-gitlab.git
cd tcctech-gitlab

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GitLab URL and API token
```

### 2. GitLab Token Setup
1. Go to your GitLab instance → **User Settings** → **Access Tokens**
2. Create token with scopes: `api`, `read_repository`, `read_user`
3. Add to your `.env` file:
```bash
GITLAB_URL=https://your-gitlab-instance.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
```

### 3. Launch Interactive Menu
```bash
python glt_menu.py
```

Choose from 9 numbered options:
1. 🔄 **Rename Branches** - Bulk trunk→main conversion
2. 📊 **Generate Executive Dashboard** - Create HTML analytics reports
3. 📅 **Generate Weekly Report** - Team productivity insights
4. 📧 **Send Report Email** - Deliver reports via email
5. 🎯 **Create Issues** - Bulk issue creation from templates
6. 📈 **Analyze Projects** - Deep project analytics with health scoring
7. 💾 **Export Analytics** - Export data to Excel/JSON
8. 📋 **Generate Code Changes Report** - Track development activity
9. 👋 **Exit**

### 4. Try Your First Operation
**Generate Executive Dashboard (Option 2):**
- Enter group IDs: `1721,1267,1269`
- Get beautiful HTML dashboard with team metrics
- Optionally email to stakeholders

## ✨ Core Features

### 🔄 Branch Modernization
Transform your Git workflow across all repositories safely:
```bash
# Preview changes first (always recommended)
python glt_menu.py → Option 1 → Enter groups → Dry run preview

# Execute bulk rename with safety checks
python scripts/rename_branches.py --groups "AI-ML-Services" --old-branch trunk --new-branch main
```

**Safety Features:**
- Dry-run preview mode
- Protected branch detection
- Rollback support
- Real-time progress tracking

### 📊 Executive Dashboards
Generate professional HTML reports with one command:
```bash
# Interactive menu approach
python glt_menu.py → Option 2

# Direct command approach  
python scripts/generate_executive_dashboard.py --groups 1721,1267,1269 --output dashboard.html
```

**Dashboard Features:**
- Project health scoring (A-F grades)
- Visual analytics with charts
- Team productivity metrics
- Mobile-responsive design
- Email delivery integration

### 📈 Weekly Team Reports
Automated productivity reports with advanced analytics:
```bash
# Generate and email weekly report
python scripts/weekly_reports.py --groups 1721,1267,1269 --email team@company.com
```

**Advanced Analytics:**
- Three-method branch analysis
- Contributor deduplication across projects
- Person-focused productivity views
- Issue tracking and resolution metrics
- Professional HTML email templates

### 🎯 Issue Management
Create GitLab issues from markdown files with templates:
```bash
# Add markdown files to issues/ folder, then:
python scripts/sync_issues.py PROJECT_ID --dry-run  # Preview
python scripts/sync_issues.py PROJECT_ID --use-api  # Create
```

**Template Features:**
- YAML frontmatter support
- Variable substitution
- Bulk CSV import
- Epic, research, and ML experiment templates

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- GitLab API token with appropriate permissions
- Git (for repository operations)

### Environment Configuration
```bash
# Required variables in .env
GITLAB_URL=https://your-gitlab-instance.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Optional email configuration for reports
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-app-password
```

### Verification
Test your setup:
```bash
# Verify configuration
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✓ GitLab URL:', os.getenv('GITLAB_URL'))
print('✓ Token configured:', 'Yes' if os.getenv('GITLAB_TOKEN') else 'No')
"

# Test API access
python scripts/analyze_projects.py --help
```

## 📖 Usage Examples

### Weekly Team Sync
```bash
# Generate comprehensive weekly report
python scripts/weekly_reports.py \
  --groups 1721,1267,1269 \
  --email team@company.com \
  --team-name "AI Development Team"
```

### Repository Modernization
```bash
# Safe bulk branch renaming
python scripts/rename_branches.py \
  --groups "AI-ML-Services" "Research Repos" \
  --dry-run  # Preview first
```

### Sprint Planning Automation
```bash
# Create issues from planning documents
# 1. Add .md files to issues/ folder with YAML frontmatter
# 2. Sync to GitLab
python scripts/sync_issues.py my-project --use-api
```

## 🔧 Command Reference

### Interactive Menu (Recommended)
```bash
python glt_menu.py              # Launch numbered menu interface
```

### Direct Script Access
```bash
# Branch operations
python scripts/rename_branches.py --groups "GroupName" --dry-run

# Dashboard generation
python scripts/generate_executive_dashboard.py --groups 1721,1267 --output report.html

# Analytics export
python scripts/export_analytics.py --projects 123,456 --output analytics.xlsx

# Issue creation
python scripts/create_issues.py ProjectName --template feature
```

## ⚙️ Configuration

The tool uses a flexible configuration system:

1. **Command line arguments** (highest priority)
2. **Environment variables** (.env file)
3. **Configuration files** (config.yaml)

See [Configuration Guide](docs/ANALYTICS_GUIDE.md) for detailed setup options.

## 🧪 Testing

Run the comprehensive test suite:
```bash
# Run all tests with coverage (80% minimum)
pytest

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api          # API tests only
```

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| `401 Unauthorized` | Check GitLab token in `.env` file |
| `Group not found` | Verify group names/IDs and permissions |
| Empty dashboard | Ensure groups have recent activity (last 30 days) |
| Email delivery fails | Configure SMTP settings in `.env` |

**Health check command:**
```bash
python scripts/analyze_projects.py --help  # Should display help if setup is correct
```

## 📁 Project Structure

```
gitlab-tools/
├── glt_menu.py              # Interactive menu interface
├── scripts/                 # CLI entry points
│   ├── rename_branches.py   # Bulk branch operations
│   ├── weekly_reports.py    # Team productivity analytics
│   ├── create_issues.py     # Issue management
│   └── ...
├── src/                     # Core library
│   ├── api/                # GitLab API client
│   ├── services/           # Business logic
│   ├── models/             # Data models
│   └── utils/              # Shared utilities
├── templates/              # Issue templates
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## 📚 Documentation

- [Analytics Guide](docs/ANALYTICS_GUIDE.md) - Advanced analytics features and configuration
- [CLAUDE.md](CLAUDE.md) - Developer guide for code contributions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure 80% test coverage: `pytest --cov=src`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **Repository**: https://github.com/tkhongsap/tcctech-gitlab
- **Issues**: https://github.com/tkhongsap/tcctech-gitlab/issues

---

*Built with ❤️ for teams managing GitLab at scale*