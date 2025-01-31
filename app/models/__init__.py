from app.extensions import db
from .activity import Activity
from .lead import Lead
from .campaign import Campaign
from .comment import Comment
from .email_tracking import EmailTracking

# Dit zorgt ervoor dat alle modellen beschikbaar zijn wanneer we 'from app.models import *' gebruiken
__all__ = ['Activity', 'Comment', 'Campaign', 'EmailTracking', 'Lead'] 