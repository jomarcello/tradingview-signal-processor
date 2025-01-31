from flask import Blueprint, render_template, request, jsonify
from app.models import Campaign, EmailTemplate
from app import db

bp = Blueprint('campaigns', __name__, url_prefix='/campaigns')

@bp.route('/')
def index():
    templates = EmailTemplate.query.all()
    campaigns = Campaign.query.all()
    return render_template('campaigns/index.html', templates=templates, campaigns=campaigns) 