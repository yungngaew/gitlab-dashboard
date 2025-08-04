"""Template files for GitLab Tools."""

# Weekly report email template available conditionally
try:
    from .weekly_report_email import WeeklyReportEmailTemplate
    __all__ = ['WeeklyReportEmailTemplate']
except ImportError:
    __all__ = []