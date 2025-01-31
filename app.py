from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Database_luxuryrentals.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Leads model
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    email_opened = db.Column(db.Boolean, default=False)

# Update model initialisatie
model_name = "deepseek-ai/deepseek-coder-6.7b-base"
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
    # Fallback naar een kleiner model indien nodig
    model_name = "deepseek-ai/deepseek-coder-1.3b-base"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )

# Home route
@app.route('/')
def dashboard():
    total_leads = Lead.query.count()
    opened_emails = Lead.query.filter_by(email_opened=True).count()
    not_opened = total_leads - opened_emails
    leads_by_country = db.session.query(Lead.country, db.func.count(Lead.id)).group_by(Lead.country).all()
    
    return render_template('dashboard.html', total_leads=total_leads, opened_emails=opened_emails,
                           not_opened=not_opened, leads_by_country=leads_by_country)

# Route to add new lead
@app.route('/add', methods=['POST'])
def add_lead():
    name = request.form['name']
    email = request.form['email']
    country = request.form['country']
    city = request.form['city']
    new_lead = Lead(name=name, email=email, country=country, city=city)
    db.session.add(new_lead)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/generate', methods=['POST'])
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

if __name__ == '__main__':
    with app.app_context():  # Fix: Add application context
        db.create_all()
    app.run(host='0.0.0.0', port=8000)