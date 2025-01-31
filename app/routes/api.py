from flask import Blueprint, jsonify, request
from app.models import Lead, Comment, Activity
from app import db
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/leads', methods=['GET'])
def get_leads():
    # Filter parameters
    engagement = request.args.get('engagement')
    email_opened = request.args.get('emailOpened')
    link_clicked = request.args.get('linkClicked')
    date_added = request.args.get('dateAdded')
    search = request.args.get('search')
    
    # Start with base query
    query = Lead.query
    
    # Apply filters
    if engagement:
        if engagement == 'high':
            query = query.filter(Lead.engagement_score >= 3)
        elif engagement == 'medium':
            query = query.filter(Lead.engagement_score == 2)
        elif engagement == 'low':
            query = query.filter(Lead.engagement_score <= 1)
    
    if email_opened:
        query = query.filter(Lead.last_email_opened.isnot(None))
    
    if link_clicked:
        query = query.filter(Lead.last_link_clicked.isnot(None))
    
    if date_added:
        date = datetime.strptime(date_added, '%Y-%m-%d')
        query = query.filter(db.func.date(Lead.created_at) == date)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Lead.name.ilike(search_term),
                Lead.email.ilike(search_term),
                Lead.instagram_username.ilike(search_term)
            )
        )
    
    # Execute query and return results
    leads = query.order_by(Lead.updated_at.desc()).all()
    return jsonify([lead.to_dict() for lead in leads])

@bp.route('/leads/<int:lead_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    
    if request.method == 'GET':
        return jsonify(lead.to_dict())
    
    elif request.method == 'PUT':
        data = request.json
        
        # Update basic fields
        for field in ['name', 'email', 'instagram_username', 'instagram_url', 
                     'external_url', 'status', 'notes']:
            if field in data:
                setattr(lead, field, data[field])
        
        # Log status change if it happened
        if 'status' in data:
            activity = Activity(
                lead_id=lead.id,
                action='status_changed',
                details=f"Status changed to {data['status']}"
            )
            db.session.add(activity)
        
        db.session.commit()
        return jsonify(lead.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(lead)
        db.session.commit()
        return '', 204

@bp.route('/leads/<int:lead_id>/status', methods=['PUT'])
def update_lead_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    data = request.json
    
    if 'status' in data:
        lead.status = data['status']
        
        # Log activity
        activity = Activity(
            lead_id=lead.id,
            action='status_changed',
            details=f"Status changed to {data['status']}"
        )
        db.session.add(activity)
        
        db.session.commit()
        return jsonify(lead.to_dict())
    
    return jsonify({'error': 'No status provided'}), 400

@bp.route('/leads/<int:lead_id>/comments', methods=['GET', 'POST'])
def manage_comments(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    
    if request.method == 'GET':
        comments = Comment.query.filter_by(lead_id=lead_id)\
                              .order_by(Comment.created_at.desc())\
                              .all()
        return jsonify([{
            'id': c.id,
            'content': c.content,
            'created_at': c.created_at.isoformat()
        } for c in comments])
    
    elif request.method == 'POST':
        data = request.json
        comment = Comment(
            lead_id=lead_id,
            content=data['content']
        )
        db.session.add(comment)
        
        # Log activity
        activity = Activity(
            lead_id=lead_id,
            action='comment_added',
            details=f"New comment added"
        )
        db.session.add(activity)
        
        db.session.commit()
        return jsonify({
            'id': comment.id,
            'content': comment.content,
            'created_at': comment.created_at.isoformat()
        }) 