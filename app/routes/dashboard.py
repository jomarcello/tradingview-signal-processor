from flask import Blueprint, render_template

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    # Mock data voor het dashboard
    user = {
        'name': 'Anna T.'
    }
    
    revenue = {
        'clothes': 321458,
        'electronics': 314412,
        'other': 123758
    }
    
    items = {
        'clothes': 150890,
        'electronics': 32231,
        'other': 89412
    }
    
    return render_template('dashboard/index.html',
                         user=user,
                         revenue=revenue,
                         items=items)