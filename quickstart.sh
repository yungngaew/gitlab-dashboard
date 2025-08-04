#!/bin/bash

# Quick start script for GitLab issue sync

echo "GitLab Issue Sync - Quick Start"
echo "==============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    echo "# Add your GitLab API token here" > .env
    echo "GITLAB_API_TOKEN=your-token-here" >> .env
    echo "✓ .env file created - Please update with your GitLab token"
else
    echo "✓ .env file found"
fi

# Check if issues folder exists
if [ ! -d issues ]; then
    echo "✓ Issues folder will be created on first run"
else
    echo "✓ Issues folder found"
    echo ""
    echo "Current issues:"
    ls -la issues/*.md issues/*.txt 2>/dev/null | grep -v "^d" | awk '{print "  - " $9}'
fi

echo ""
echo "Ready to sync issues to GitLab!"
echo ""
echo "Commands:"
echo "  Preview:  python3 sync_issues_simple.py --dry-run"
echo "  Create:   python3 sync_issues_simple.py"
echo ""
echo "Project: ds-and-ml-research-sandbox/research-repos/issues-generator-automation"
echo "GitLab:  https://git.lab.tcctech.app"
echo ""