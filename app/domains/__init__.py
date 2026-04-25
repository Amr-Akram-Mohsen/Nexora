# Import ALL models so SQLAlchemy sees them
from .user.models import *
from .article.models import *
from .item.models import *
from .interaction.models import *
from .system.models import *
from .external.models import *
from .recommendation.models import *

# IMPORTANT: relationships file MUST be imported too
from .relationships import *
