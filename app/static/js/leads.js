document.addEventListener('DOMContentLoaded', function() {
    // Initialiseer dragula voor drag-and-drop
    const drake = dragula([
        document.querySelector('#newLeads'),
        document.querySelector('#contacted'),
        document.querySelector('#followUp'),
        document.querySelector('#hotLeads')
    ]);

    // Update lead status na drag-and-drop
    drake.on('drop', function(el, target, source) {
        const leadId = el.dataset.leadId;
        const newStatus = target.id;
        updateLeadStatus(leadId, newStatus);
    });

    // Laad initiële leads
    loadLeads();

    // Event listeners voor filters en zoeken
    document.querySelector('#searchInput').addEventListener('input', debounce(filterLeads, 300));
});

// Laad leads van de server
async function loadLeads() {
    try {
        const response = await fetch('/api/leads');
        const leads = await response.json();
        
        // Reset containers
        document.querySelectorAll('.kanban-container').forEach(container => {
            container.innerHTML = '';
        });

        // Verdeel leads over kolommen
        leads.forEach(lead => {
            const card = createLeadCard(lead);
            const container = document.querySelector(`#${lead.status}`);
            if (container) {
                container.appendChild(card);
            }
        });

        // Update tellers
        updateCounters();
    } catch (error) {
        console.error('Error loading leads:', error);
        showError('Fout bij het laden van leads');
    }
}

// Maak een lead kaart
function createLeadCard(lead) {
    const template = document.querySelector('#leadCardTemplate');
    const card = template.content.cloneNode(true);
    
    // Vul kaart data
    const container = card.querySelector('.lead-card');
    container.dataset.leadId = lead.id;
    
    container.querySelector('.card-title').textContent = lead.name;
    container.querySelector('.instagram-username').textContent = lead.instagram_username;
    container.querySelector('.email').textContent = lead.email;
    container.querySelector('.score').textContent = lead.engagement_score;

    // Event listeners voor knoppen
    container.querySelector('.btn-edit').addEventListener('click', () => editLead(lead.id));
    container.querySelector('.btn-comment').addEventListener('click', () => showComments(lead.id));
    container.querySelector('.btn-email').addEventListener('click', () => sendEmail(lead.id));

    return container;
}

// Update lead status
async function updateLeadStatus(leadId, newStatus) {
    try {
        const response = await fetch(`/api/leads/${leadId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (!response.ok) {
            throw new Error('Status update failed');
        }

        updateCounters();
    } catch (error) {
        console.error('Error updating lead status:', error);
        showError('Fout bij het updaten van lead status');
    }
}

// Update tellers voor elke kolom
function updateCounters() {
    document.querySelector('#newLeadsCount').textContent = 
        document.querySelector('#newLeads').children.length;
    document.querySelector('#contactedCount').textContent = 
        document.querySelector('#contacted').children.length;
    document.querySelector('#followUpCount').textContent = 
        document.querySelector('#followUp').children.length;
    document.querySelector('#hotLeadsCount').textContent = 
        document.querySelector('#hotLeads').children.length;
}

// Utility functies
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showError(message) {
    // Implementeer error notificatie
    alert(message);
} 