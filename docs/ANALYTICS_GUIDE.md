# GitLab Analytics Guide

This guide covers the advanced analytics features available in GitLab Tools.

## Overview

The analytics module provides comprehensive insights into your GitLab projects and groups, including:

- Repository activity metrics
- Code health assessment
- Trend analysis over time
- Project comparisons
- Smart recommendations

## Quick Start

### Basic Project Analytics

```bash
# Get basic metrics for a project
python scripts/analyze_projects.py --project my-project

# Save to file
python scripts/analyze_projects.py --project my-project -o report.md
```

### Trend Analysis

```bash
# Analyze trends over 90 days with health scoring
python scripts/analyze_projects.py --project my-project --trends --days 90

# Generate HTML dashboard
python scripts/analyze_projects.py --project my-project --trends --html -o dashboard.html
```

## Features

### 1. Health Scoring

Projects are automatically assessed and given a health score (0-100) and grade (A-F) based on:

- **Commit Activity** - Frequency and consistency of commits
- **Issue Resolution** - How quickly issues are resolved
- **Merge Request Efficiency** - Merge rate and turnaround time
- **Contributor Diversity** - Number of active contributors

#### Grade Scale:
- **A (90-100)**: Excellent health
- **B (80-89)**: Good health
- **C (70-79)**: Average health
- **D (60-69)**: Below average
- **F (0-59)**: Needs attention

### 2. Smart Recommendations

The system provides actionable recommendations based on detected issues:

- 📉 Declining commit activity
- 🐌 Slow issue resolution
- 👤 Low contributor diversity
- ⏰ Overdue issues
- 🚫 Low merge request acceptance rate

### 3. Trend Analysis

Track how metrics change over time:

```bash
# 30-day trends (default)
python scripts/analyze_projects.py --project my-project --trends

# Custom time period
python scripts/analyze_projects.py --project my-project --trends --days 180
```

Trends include:
- Commit frequency patterns
- Issue creation/resolution rates
- Merge request velocity
- Contributor activity

### 4. Project Comparison

Compare multiple projects side-by-side:

```bash
# Compare by project IDs
python scripts/analyze_projects.py --compare 123 456 789

# Export comparison to Excel
python scripts/export_analytics.py "compare:123,456,789" -o comparison.xlsx
```

### 5. Caching

Analytics queries are cached for 15 minutes (trends for 30 minutes) to improve performance:

```bash
# First run fetches from API and caches
python scripts/analyze_projects.py --project my-project

# Subsequent runs use cache (much faster)
python scripts/analyze_projects.py --project my-project

# Force refresh
python scripts/analyze_projects.py --project my-project --no-cache

# Clear all cache
python scripts/analyze_projects.py --project my-project --clear-cache
```

### 6. Export Formats

#### Markdown (Default)
```bash
python scripts/analyze_projects.py --project my-project -o report.md
```

#### JSON
```bash
python scripts/analyze_projects.py --project my-project --format json -o data.json
```

#### HTML Dashboard
```bash
python scripts/analyze_projects.py --project my-project --trends --html -o dashboard.html
```

#### Excel
```bash
python scripts/export_analytics.py my-project -o report.xlsx
```

## Excel Export

The Excel export creates a comprehensive workbook with multiple sheets:

### For Single Projects:
- **Overview**: Project information and summary
- **Commits**: Commit statistics and author breakdown
- **Issues**: Issue metrics and label analysis
- **Merge Requests**: MR statistics
- **Trends**: Time-series data (if --trends used)

### For Comparisons:
- **Comparison**: Side-by-side project metrics
- **Rankings**: Projects ranked by various metrics
- **Charts**: Visual comparisons (requires pandas)

## Advanced Usage

### Group Analytics

Analyze all projects in a group:

```bash
# Basic group metrics
python scripts/analyze_projects.py --group "AI-ML-Services"

# Group trends (aggregated)
python scripts/analyze_projects.py --group "AI-ML-Services" --trends
```

### Custom Metrics

The analytics system is extensible. You can add custom metrics by:

1. Extending `AdvancedAnalytics` class
2. Adding new metric calculations
3. Including in health score factors

### API Rate Limiting

The analytics respect GitLab's rate limits:
- Configurable requests per second (default: 3)
- Automatic retry with exponential backoff
- Caching reduces API calls

## Interpreting Results

### Commit Metrics
- **Total Commits**: Activity level indicator
- **Weekly Average**: Consistency measure
- **Unique Authors**: Team engagement
- **Commit Trend**: Rising (>0) or falling (<0)

### Issue Metrics
- **Open/Closed Ratio**: Backlog health
- **Average Resolution Days**: Team responsiveness
- **Overdue Issues**: Planning accuracy

### Merge Request Metrics
- **Merge Rate**: Code review efficiency
- **Average Merge Time**: Review turnaround
- **Authors**: Active contributors

## Best Practices

1. **Regular Monitoring**: Run analytics weekly to track trends
2. **Act on Recommendations**: Address issues highlighted by the system
3. **Compare Similar Projects**: Use comparison for benchmarking
4. **Cache Wisely**: Use cache for repeated queries, clear when needed
5. **Export for Sharing**: Use Excel/HTML for stakeholder reports

## Troubleshooting

### Common Issues

1. **"Group not found"**: Check group name spelling and permissions
2. **"No data"**: Ensure project has recent activity
3. **"Rate limited"**: Wait or reduce request frequency
4. **"Cache issues"**: Use --clear-cache to reset

### Debug Mode

```bash
# Enable debug logging
python scripts/analyze_projects.py --project my-project --log-level DEBUG
```

## Examples

### Weekly Team Report
```bash
# Generate comprehensive report for team meeting
python scripts/export_analytics.py my-project --trends --days 7 -o weekly_report.xlsx
```

### Monthly Health Check
```bash
# Check all projects in a group
for project in project1 project2 project3; do
    python scripts/analyze_projects.py --project $project --trends --format json -o ${project}_health.json
done
```

### Stakeholder Dashboard
```bash
# Create visual dashboard for executives
python scripts/analyze_projects.py --group "All-Projects" --trends --html -o executive_dashboard.html
```