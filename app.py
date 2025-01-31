from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

# Creëer de Flask applicatie
application = Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Database_luxuryrentals.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(application)

# Voeg deze regel toe voor de port configuratie
port = int(os.getenv('PORT', 8000))

# Define the Leads model
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    email_opened = db.Column(db.Boolean, default=False)

# Update model initialisatie
model_name = "deepseek-ai/deepseek-coder-1.3b-base"  # We gebruiken het kleinere model voor nu
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

try:
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
except Exception as e:
    print(f"Error loading model: {e}")

# Home route
@application.route('/')
def dashboard():
    total_leads = Lead.query.count()
    opened_emails = Lead.query.filter_by(email_opened=True).count()
    not_opened = total_leads - opened_emails
    leads_by_country = db.session.query(Lead.country, db.func.count(Lead.id)).group_by(Lead.country).all()
    
    return render_template('dashboard.html', total_leads=total_leads, opened_emails=opened_emails,
                           not_opened=not_opened, leads_by_country=leads_by_country)

# Route to add new lead
@application.route('/add', methods=['POST'])
def add_lead():
    name = request.form['name']
    email = request.form['email']
    country = request.form['country']
    city = request.form['city']
    new_lead = Lead(name=name, email=email, country=country, city=city)
    db.session.add(new_lead)
    db.session.commit()
    return redirect(url_for('dashboard'))

@application.route('/generate', methods=['POST'])
def generate_code():
    data = request.json
    prompt = data.get('prompt', '')
    
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        inputs.input_ids,
        max_length=512,
        temperature=0.7,
        top_p=0.95,
        num_return_sequences=1
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return jsonify({'response': response})

# Maak het app object beschikbaar voor Gunicorn
app = application

if __name__ == '__main__':
    with application.app_context():
        db.create_all()
    application.run(host='0.0.0.0', port=port)