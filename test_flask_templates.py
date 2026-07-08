import os
import shutil
from flask import Flask, Blueprint, render_template

os.makedirs('templates_test/global_shared', exist_ok=True)
os.makedirs('templates_test/blueprint_public', exist_ok=True)

with open('templates_test/global_shared/shared.html', 'w') as f:
    f.write('I am shared!')

with open('templates_test/blueprint_public/index.html', 'w') as f:
    f.write('{% include "global_shared/shared.html" %}')

app = Flask(__name__, template_folder='templates_test')
bp = Blueprint('public', __name__, template_folder='templates_test/blueprint_public')

@bp.route('/')
def index():
    return render_template('index.html')

app.register_blueprint(bp)

with app.test_request_context('/'):
    print('RESULT:', app.view_functions['public.index']())

shutil.rmtree('templates_test')
