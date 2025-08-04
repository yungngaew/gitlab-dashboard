"""Business logic services."""

from .issue_service import IssueService
from .branch_service import BranchService
from .analytics import GitLabAnalytics

# Weekly reports available conditionally
try:
    from .weekly_reports import WeeklyProductivityReporter
    from .email_service import EmailService, WeeklyReportEmailSender
    __all__ = ['IssueService', 'BranchService', 'GitLabAnalytics', 'WeeklyProductivityReporter', 'EmailService', 'WeeklyReportEmailSender']
except ImportError:
    __all__ = ['IssueService', 'BranchService', 'GitLabAnalytics']