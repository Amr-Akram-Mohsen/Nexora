import os
os.environ["FLASK_APP"] = "manage.py"

from app import create_app
from app.domains.interaction.service.analytics import get_analytics_dashboard_data

app = create_app()
with app.app_context():
    try:
        data = get_analytics_dashboard_data()
        print("Success!", data.keys())
    except Exception as e:
        import traceback
        traceback.print_exc()
