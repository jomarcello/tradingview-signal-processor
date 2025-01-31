class CampaignManager {
    constructor() {
        this.editor = null;
        this.initializeQuillEditor();
        this.initializeEventListeners();
        this.loadTemplates();
    }

    initializeQuillEditor() {
        this.editor = new Quill('#editor', {
            theme: 'snow',
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    ['link', 'image'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'header': [1, 2, 3, false] }],
                    ['clean']
                ]
            }
        });
    }

    async saveTemplate(event) {
        event.preventDefault();
        const form = event.target;
        
        try {
            const response = await fetch('/api/templates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: form.name.value,
                    subject: form.subject.value,
                    body_html: this.editor.root.innerHTML
                })
            });
            
            const result = await response.json();
            showAlert('Template succesvol opgeslagen');
            this.loadTemplates();
        } catch (error) {
            showAlert('Fout bij opslaan template', 'danger');
        }
    }

    async createCampaign(event) {
        event.preventDefault();
        const form = event.target;
        
        try {
            const response = await fetch('/api/campaigns', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: form.name.value,
                    template_id: form.template_id.value,
                    scheduled_at: form.scheduled_at.value || null
                })
            });
            
            const result = await response.json();
            showAlert('Campagne succesvol aangemaakt');
            window.location.href = '/dashboard';
        } catch (error) {
            showAlert('Fout bij aanmaken campagne', 'danger');
        }
    }

    async loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const templates = await response.json();
            
            const select = document.querySelector('select[name="template_id"]');
            select.innerHTML = templates.map(template => `
                <option value="${template.id}">${template.name}</option>
            `).join('');
        } catch (error) {
            showAlert('Fout bij laden templates', 'danger');
        }
    }

    initializeEventListeners() {
        const templateForm = document.getElementById('templateForm');
        if (templateForm) {
            templateForm.addEventListener('submit', this.saveTemplate.bind(this));
        }

        const campaignForm = document.getElementById('campaignForm');
        if (campaignForm) {
            campaignForm.addEventListener('submit', this.createCampaign.bind(this));
        }
    }
}

// Initialiseer bij laden van de pagina
document.addEventListener('DOMContentLoaded', () => {
    const campaignManager = new CampaignManager();
}); 