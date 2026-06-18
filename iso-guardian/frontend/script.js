const fileInput = document.getElementById('iso-upload');
const analyzeBtn = document.getElementById('analyze-btn');
const loadingDiv = document.getElementById('loading');
const resultsSection = document.getElementById('results-section');
const statusCard = document.getElementById('status-card');
const riskStatus = document.getElementById('risk-status');
const riskScore = document.getElementById('risk-score');
const agentDetails = document.getElementById('agent-details');
const uploadBox = document.getElementById('upload-box');
const uploadLabelText = document.querySelector('.upload-label .text');

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        uploadLabelText.textContent = file.name;
        analyzeBtn.disabled = false;
        uploadBox.style.borderColor = 'var(--accent)';
    } else {
        uploadLabelText.textContent = 'Click to select or drag and drop an ISO file';
        analyzeBtn.disabled = true;
        uploadBox.style.borderColor = '#475569';
    }
});

analyzeBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    // Show loading
    analyzeBtn.disabled = true;
    loadingDiv.classList.remove('hidden');
    resultsSection.classList.add('hidden');

    try {
        const response = await fetch('http://localhost:8000/api/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error analyzing ISO:', error);
        alert('An error occurred during analysis: ' + error.message);
    } finally {
        analyzeBtn.disabled = false;
        loadingDiv.classList.add('hidden');
    }
});

function displayResults(data) {
    resultsSection.classList.remove('hidden');
    
    // Set status
    riskStatus.textContent = data.status.replace(/_/g, ' ');
    riskScore.textContent = data.risk_score;

    statusCard.className = 'status-card';
    if (['TRUSTED'].includes(data.status)) {
        statusCard.classList.add('trusted');
    } else if (['SUSPICIOUS', 'MODIFIED_OR_FABRICATED', 'FABRICATED_OR_INVALID', 'CORRUPTED'].includes(data.status)) {
        statusCard.classList.add('suspicious');
    } else if (['LIKELY_SAFE_BUT_UNVERIFIED'].includes(data.status)) {
        statusCard.classList.add('warning');
    } else {
        statusCard.classList.add('unknown');
    }

    // Set agent details
    agentDetails.innerHTML = '';
    
    const details = data.details;
    for (const [agentName, agentData] of Object.entries(details)) {
        const card = document.createElement('div');
        card.className = 'agent-detail-card';
        
        const title = document.createElement('h4');
        title.textContent = agentName.charAt(0).toUpperCase() + agentName.slice(1) + ' Agent';
        
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(agentData, null, 2);
        
        card.appendChild(title);
        card.appendChild(pre);
        agentDetails.appendChild(card);
    }
}
