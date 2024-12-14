from .company_matcher import CompanyMatcherService
from .outreach_service import OutreachService

# This makes the services available directly from the package
# Now you can use:
# from services import CompanyMatcherService, OutreachService
# instead of:
# from services.company_matcher import CompanyMatcherService
# from services.outreach_service import OutreachService

__all__ = [
    'CompanyMatcherService',
    'OutreachService',
]

# Version info
__version__ = '0.1.0'

# You could also add package-level configuration here
DEFAULT_MIN_SCORE = 0.6
DEFAULT_NUM_MATCHES = 2 