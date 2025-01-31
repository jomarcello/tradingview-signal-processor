from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.models import Lead
from app import db
import csv
import io
import uuid  # Voor het genereren van tijdelijke email placeholders

bp = Blueprint('leads', __name__, url_prefix='/leads')

REQUIRED_COLUMNS = ['Name', 'instagram_username', 'instagram_url', 'external_url']  # Email niet meer verplicht

@bp.route('/')
def index():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template('leads/index.html', leads=leads)

@bp.route('/import', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('Geen bestand geüpload', 'error')
        return redirect(url_for('leads.index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Geen bestand geselecteerd', 'error')
        return redirect(url_for('leads.index'))
    
    if not file.filename.endswith('.csv'):
        flash('Alleen CSV bestanden zijn toegestaan', 'error')
        return redirect(url_for('leads.index'))
    
    try:
        # Lees CSV bestand
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        
        # Detecteer de delimiter
        sample = stream.read(1024)
        stream.seek(0)
        if ';' in sample:
            delimiter = ';'
        else:
            delimiter = ','
            
        csv_input = csv.DictReader(stream, delimiter=delimiter)
        
        # Debug: Print kolomnamen
        flash(f"Gevonden kolommen: {', '.join(csv_input.fieldnames)}", 'info')
        
        # Controleer kolommen
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in csv_input.fieldnames]
        if missing_columns:
            flash(f'Missende kolommen in CSV: {", ".join(missing_columns)}. Gevonden kolommen: {", ".join(csv_input.fieldnames)}', 'error')
            return redirect(url_for('leads.index'))
        
        added = 0
        skipped = 0
        errors = []
        row_number = 1
        
        for row in csv_input:
            row_number += 1
            
            # Debug: Print ruwe rij data
            if row_number <= 3:
                flash(f"Rij {row_number} data: {row}", 'info')
            
            # Controleer op lege verplichte velden
            empty_fields = [
                field for field in REQUIRED_COLUMNS 
                if (field not in row or 
                    not row.get(field) or 
                    row.get(field).strip() == '' or 
                    row.get(field).strip().upper() == 'NULL')
            ]
            if empty_fields:
                errors.append(f"Rij {row_number}: Lege velden: {', '.join(empty_fields)}")
                skipped += 1
                continue
            
            # Genereer een tijdelijke unieke email als er geen email is
            email = row.get('Email', '').strip()
            if not email or email.upper() == 'NULL':
                # Gebruik instagram username als basis voor de tijdelijke email
                username = row['instagram_username'].strip()
                email = f"pending_{username}_{uuid.uuid4().hex[:8]}@pending.com"
            
            # Controleer op duplicate email
            if Lead.query.filter_by(email=email).first():
                errors.append(f"Rij {row_number}: Email {email} bestaat al")
                skipped += 1
                continue
            
            # Maak nieuwe lead
            try:
                lead = Lead(
                    name=row['Name'].strip(),
                    email=email,
                    instagram_username=row['instagram_username'].strip(),
                    instagram_url=row['instagram_url'].strip(),
                    external_url=row['external_url'].strip()
                )
                db.session.add(lead)
                added += 1
            except Exception as e:
                errors.append(f"Rij {row_number}: Error bij toevoegen: {str(e)}")
                skipped += 1
                continue
        
        db.session.commit()
        
        # Toon feedback
        flash(f'{added} leads toegevoegd, {skipped} overgeslagen', 'success')
        if errors:
            if len(errors) > 10:
                errors = errors[:10] + [f"... en {len(errors) - 10} andere errors"]
            flash('Errors:\n' + '\n'.join(errors), 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error bij importeren: {str(e)}', 'error')
    
    return redirect(url_for('leads.index'))