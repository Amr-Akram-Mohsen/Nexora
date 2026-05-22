# Import ALL models so SQLAlchemy sees them (order matters for string relationships).
from .user.models import *
from .content.models import *
from .item.models import *
from .interaction.models import *
from .recommendation.models import *
from .external.models import *
from .system.models import *

# IMPORTANT: relationships file MUST be imported too
from .relationships import *
