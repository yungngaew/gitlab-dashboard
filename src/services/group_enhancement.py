"""Group enhancement service for business-friendly group names and metadata."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from ..api import GitLabClient
from ..utils.logger import OperationLogger

logger = logging.getLogger(__name__)

# Business-friendly group name mappings
GROUP_BUSINESS_NAMES = {
    1721: "AI & Machine Learning Services",
    1267: "Research & Development Labs", 
    1269: "Core Platform Engineering",
    1270: "Data Science & Analytics",
    1268: "Infrastructure & DevOps",
    1266: "Product Development",
    1265: "Quality Assurance & Testing",
    1264: "Security & Compliance",
    1263: "Business Intelligence",
    1262: "Customer Solutions"
}

# Group descriptions for enhanced context
GROUP_DESCRIPTIONS = {
    1721: "Advanced AI/ML services including RAG pipelines, model training, and intelligent automation solutions",
    1267: "Cutting-edge research projects, experimental technologies, and proof-of-concept developments", 
    1269: "Core platform infrastructure, APIs, and foundational services that power our ecosystem",
    1270: "Data analytics, business intelligence, and statistical modeling teams",
    1268: "Infrastructure automation, CI/CD pipelines, and platform reliability engineering",
    1266: "Product feature development, user experience design, and customer-facing applications",
    1265: "Quality assurance frameworks, automated testing, and software validation processes",
    1264: "Security protocols, compliance management, and risk assessment tools",
    1263: "Business metrics, reporting dashboards, and executive analytics platforms",
    1262: "Custom client solutions, professional services, and integration projects"
}

class GroupEnhancementService:
    """Service for enhancing group information with business context."""
    
    def __init__(self, client: GitLabClient):
        """Initialize group enhancement service.
        
        Args:
            client: GitLab API client
        """
        self.client = client
        self._group_cache = {}
        self._cache_expiry = {}
    
    def get_enhanced_group_info(self, group_id: int) -> Dict[str, Any]:
        """Get enhanced group information with business-friendly names.
        
        Args:
            group_id: GitLab group ID
            
        Returns:
            Enhanced group information dictionary
        """
        # Check cache first
        cache_key = f"group_{group_id}"
        if (cache_key in self._group_cache and 
            cache_key in self._cache_expiry and 
            self._cache_expiry[cache_key] > datetime.now()):
            return self._group_cache[cache_key]
        
        with OperationLogger(logger, "group enhancement", group_id=group_id):
            try:
                # Get group data from GitLab API
                group_data = self.client.get(f"groups/{group_id}")
                
                enhanced_info = {
                    'id': group_id,
                    'name': group_data.get('name', f'Group {group_id}'),
                    'full_name': group_data.get('full_name', ''),
                    'path': group_data.get('path', ''),
                    'description': group_data.get('description', ''),
                    'business_name': GROUP_BUSINESS_NAMES.get(group_id, group_data.get('name', f'Group {group_id}')),
                    'business_description': GROUP_DESCRIPTIONS.get(group_id, group_data.get('description', '')),
                    'visibility': group_data.get('visibility', 'private'),
                    'created_at': group_data.get('created_at', ''),
                    'web_url': group_data.get('web_url', ''),
                    'avatar_url': group_data.get('avatar_url', ''),
                    'projects_count': len(self._get_group_projects(group_id)),
                    'subgroups_count': len(self._get_subgroups(group_id)),
                    'last_activity_at': self._get_group_last_activity(group_id),
                    'enhancement_metadata': {
                        'has_business_name': group_id in GROUP_BUSINESS_NAMES,
                        'has_business_description': group_id in GROUP_DESCRIPTIONS,
                        'enhanced_at': datetime.now().isoformat()
                    }
                }
                
                # Cache for 1 hour
                self._group_cache[cache_key] = enhanced_info
                self._cache_expiry[cache_key] = datetime.now() + timedelta(hours=1)
                
                return enhanced_info
                
            except Exception as e:
                logger.error(f"Failed to enhance group {group_id}: {e}")
                # Return fallback info
                return {
                    'id': group_id,
                    'name': f'Group {group_id}',
                    'business_name': GROUP_BUSINESS_NAMES.get(group_id, f'Group {group_id}'),
                    'business_description': GROUP_DESCRIPTIONS.get(group_id, ''),
                    'error': str(e),
                    'enhancement_metadata': {
                        'has_business_name': group_id in GROUP_BUSINESS_NAMES,
                        'has_business_description': group_id in GROUP_DESCRIPTIONS,
                        'enhanced_at': datetime.now().isoformat(),
                        'fallback_used': True
                    }
                }
    
    def get_multiple_groups_info(self, group_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get enhanced information for multiple groups.
        
        Args:
            group_ids: List of GitLab group IDs
            
        Returns:
            Dictionary mapping group IDs to enhanced info
        """
        groups_info = {}
        
        for group_id in group_ids:
            groups_info[group_id] = self.get_enhanced_group_info(group_id)
        
        return groups_info
    
    def _get_group_projects(self, group_id: int) -> List[Dict]:
        """Get projects in a group."""
        try:
            return list(self.client._paginated_get(
                f"groups/{group_id}/projects",
                params={"include_subgroups": "true", "archived": "false"}
            ))
        except Exception:
            return []
    
    def _get_subgroups(self, group_id: int) -> List[Dict]:
        """Get subgroups of a group."""
        try:
            return list(self.client._paginated_get(f"groups/{group_id}/subgroups"))
        except Exception:
            return []
    
    def _get_group_last_activity(self, group_id: int) -> Optional[str]:
        """Get the last activity timestamp for a group."""
        try:
            projects = self._get_group_projects(group_id)
            last_activities = []
            
            for project in projects:
                if project.get('last_activity_at'):
                    last_activities.append(project['last_activity_at'])
            
            if last_activities:
                # Return the most recent activity
                return max(last_activities)
            
            return None
        except Exception:
            return None
    
    def get_group_hierarchy(self, group_id: int) -> Dict[str, Any]:
        """Get the complete hierarchy for a group.
        
        Args:
            group_id: Root group ID
            
        Returns:
            Hierarchical group structure
        """
        with OperationLogger(logger, "group hierarchy", group_id=group_id):
            root_group = self.get_enhanced_group_info(group_id)
            subgroups = self._get_subgroups(group_id)
            
            hierarchy = {
                'root': root_group,
                'subgroups': [],
                'total_projects': root_group.get('projects_count', 0),
                'total_subgroups': len(subgroups)
            }
            
            for subgroup in subgroups:
                subgroup_info = self.get_enhanced_group_info(subgroup['id'])
                hierarchy['subgroups'].append(subgroup_info)
                hierarchy['total_projects'] += subgroup_info.get('projects_count', 0)
            
            return hierarchy
    
    def suggest_business_names(self, group_ids: List[int]) -> Dict[int, Dict[str, str]]:
        """Suggest business-friendly names for groups that don't have them.
        
        Args:
            group_ids: List of group IDs to check
            
        Returns:
            Dictionary with suggestions for groups without business names
        """
        suggestions = {}
        
        for group_id in group_ids:
            if group_id not in GROUP_BUSINESS_NAMES:
                try:
                    group_data = self.client.get(f"groups/{group_id}")
                    
                    # Simple heuristics for name suggestions
                    original_name = group_data.get('name', f'Group {group_id}')
                    path = group_data.get('path', '')
                    description = group_data.get('description', '')
                    
                    # Generate suggestions based on keywords
                    suggestions[group_id] = {
                        'original_name': original_name,
                        'suggested_business_name': self._generate_business_name_suggestion(original_name, path, description),
                        'suggested_description': self._generate_description_suggestion(original_name, path, description),
                        'confidence': self._calculate_suggestion_confidence(original_name, path, description)
                    }
                    
                except Exception as e:
                    logger.warning(f"Could not generate suggestion for group {group_id}: {e}")
        
        return suggestions
    
    def _generate_business_name_suggestion(self, name: str, path: str, description: str) -> str:
        """Generate a business-friendly name suggestion."""
        # Keywords that suggest specific business functions
        keywords_map = {
            'ai': 'AI & Intelligence',
            'ml': 'Machine Learning',
            'data': 'Data Services',
            'infra': 'Infrastructure',
            'dev': 'Development',
            'ops': 'Operations',
            'security': 'Security & Compliance',
            'test': 'Quality Assurance',
            'research': 'Research & Development',
            'platform': 'Platform Engineering',
            'api': 'API Services',
            'web': 'Web Applications',
            'mobile': 'Mobile Solutions',
            'analytics': 'Analytics & Insights'
        }
        
        text_to_check = f"{name} {path} {description}".lower()
        
        for keyword, business_name in keywords_map.items():
            if keyword in text_to_check:
                return business_name
        
        # Default: Clean up the original name
        return name.replace('-', ' ').replace('_', ' ').title()
    
    def _generate_description_suggestion(self, name: str, path: str, description: str) -> str:
        """Generate a business-friendly description suggestion."""
        if description and len(description) > 10:
            return description
        
        # Generate based on name/path keywords
        text_to_check = f"{name} {path}".lower()
        
        if 'ai' in text_to_check or 'ml' in text_to_check:
            return "Advanced AI and machine learning solutions for intelligent automation"
        elif 'data' in text_to_check:
            return "Data analytics, processing, and business intelligence services"
        elif 'infra' in text_to_check or 'ops' in text_to_check:
            return "Infrastructure management and operational excellence solutions"
        elif 'security' in text_to_check:
            return "Security protocols, compliance management, and risk assessment"
        elif 'test' in text_to_check or 'qa' in text_to_check:
            return "Quality assurance, testing frameworks, and validation processes"
        else:
            return f"Business solutions and services managed by the {name} team"
    
    def _calculate_suggestion_confidence(self, name: str, path: str, description: str) -> float:
        """Calculate confidence score for suggestions (0-1)."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we have more information
        if description and len(description) > 20:
            confidence += 0.3
        
        if any(keyword in f"{name} {path}".lower() for keyword in 
               ['ai', 'ml', 'data', 'infra', 'security', 'test', 'dev', 'ops']):
            confidence += 0.2
        
        return min(1.0, confidence)

    def export_group_mappings(self, output_path: str = None) -> Dict[str, Any]:
        """Export current group mappings for documentation.
        
        Args:
            output_path: Optional file path to save mappings
            
        Returns:
            Group mappings data
        """
        mappings = {
            'business_names': GROUP_BUSINESS_NAMES,
            'descriptions': GROUP_DESCRIPTIONS,
            'export_metadata': {
                'exported_at': datetime.now().isoformat(),
                'total_mapped_groups': len(GROUP_BUSINESS_NAMES),
                'total_described_groups': len(GROUP_DESCRIPTIONS)
            }
        }
        
        if output_path:
            import json
            with open(output_path, 'w') as f:
                json.dump(mappings, f, indent=2)
            logger.info(f"Group mappings exported to: {output_path}")
        
        return mappings