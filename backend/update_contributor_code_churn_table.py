#!/usr/bin/env python3
"""Script to update existing contributor_code_churn table with missing indexes and comments."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DatabaseManager

def update_contributor_code_churn_table():
    """Update the existing contributor_code_churn table with missing indexes and comments."""
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    
    # Initialize database connection
    db_manager = DatabaseManager()
    
    if not db_manager.connect():
        print("[ERROR] Failed to connect to database")
        return False
    
    try:
        # Check if table exists
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'gitlab-activity-analysis-schema' 
            AND table_name = 'contributor_code_churn'
        );
        """
        
        table_exists = db_manager.execute_query(check_table_query)
        if not table_exists or not table_exists[0]['exists']:
            print("[ERROR] Table contributor_code_churn does not exist. Please create it first.")
            return False
        
        print("[INFO] Found existing contributor_code_churn table. Checking for missing indexes...")
        
        # Check and create missing indexes
        indexes_to_create = [
            {
                'name': 'idx_contributor_code_churn_contributor',
                'sql': 'CREATE INDEX idx_contributor_code_churn_contributor ON "gitlab-activity-analysis-schema".contributor_code_churn(contributor_name)'
            },
            {
                'name': 'idx_contributor_code_churn_project',
                'sql': 'CREATE INDEX idx_contributor_code_churn_project ON "gitlab-activity-analysis-schema".contributor_code_churn(project_id)'
            },
            {
                'name': 'idx_contributor_code_churn_period',
                'sql': 'CREATE INDEX idx_contributor_code_churn_period ON "gitlab-activity-analysis-schema".contributor_code_churn(period_start, period_end)'
            }
        ]
        
        for index in indexes_to_create:
            # Check if index exists
            check_index_query = """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE indexname = %s 
                AND schemaname = 'gitlab-activity-analysis-schema'
            );
            """
            
            index_exists = db_manager.execute_query(check_index_query, (index['name'],))
            
            if not index_exists or not index_exists[0]['exists']:
                print(f"[INFO] Creating index: {index['name']}")
                result = db_manager.execute_query(index['sql'])
                if result is not None:
                    print(f"[SUCCESS] Created index: {index['name']}")
                else:
                    print(f"[ERROR] Failed to create index: {index['name']}")
            else:
                print(f"[INFO] Index already exists: {index['name']}")
        
        # Add table and column comments
        print("[INFO] Adding table and column comments...")
        
        comments = [
            {
                'type': 'table',
                'name': 'contributor_code_churn',
                'comment': 'Stores code churn data for contributors per project and time period'
            },
            {
                'type': 'column',
                'name': 'contributor_name',
                'comment': 'Name of the contributor'
            },
            {
                'type': 'column',
                'name': 'contributor_email',
                'comment': 'Email of the contributor (optional)'
            },
            {
                'type': 'column',
                'name': 'project_id',
                'comment': 'ID of the project (foreign key to project_cache)'
            },
            {
                'type': 'column',
                'name': 'project_name',
                'comment': 'Name of the project'
            },
            {
                'type': 'column',
                'name': 'additions',
                'comment': 'Number of lines added'
            },
            {
                'type': 'column',
                'name': 'deletions',
                'comment': 'Number of lines deleted'
            },
            {
                'type': 'column',
                'name': 'changes',
                'comment': 'Total number of changes (additions + deletions)'
            },
            {
                'type': 'column',
                'name': 'period_start',
                'comment': 'Start of the analysis period'
            },
            {
                'type': 'column',
                'name': 'period_end',
                'comment': 'End of the analysis period'
            },
            {
                'type': 'column',
                'name': 'created_at',
                'comment': 'Timestamp when this record was created'
            }
        ]
        
        for comment in comments:
            if comment['type'] == 'table':
                sql = f'COMMENT ON TABLE "gitlab-activity-analysis-schema".{comment["name"]} IS %s'
            else:
                sql = f'COMMENT ON COLUMN "gitlab-activity-analysis-schema".contributor_code_churn.{comment["name"]} IS %s'
            
            result = db_manager.execute_query(sql, (comment['comment'],))
            if result is not None:
                print(f"[SUCCESS] Added comment for {comment['type']}: {comment['name']}")
            else:
                print(f"[WARNING] Failed to add comment for {comment['type']}: {comment['name']}")
        
        print("[SUCCESS] contributor_code_churn table updated successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error updating table: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db_manager.disconnect()

def main():
    """Main function."""
    print("=== Contributor Code Churn Table Update ===")
    
    if update_contributor_code_churn_table():
        print("\n[SUCCESS] Update completed successfully!")
        return 0
    else:
        print("\n[ERROR] Update failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 