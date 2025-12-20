// Feature Sharing JavaScript

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication first
    if (!Utils.checkAuth()) return;
    
    // Load agents for all dropdowns
    loadAgentsForDropdown('agent-select');
    loadAgentsForDropdown('thread-agent-select');
    loadAgentsForDropdown('editor-agent-select');
    
    // Add event listeners for thread agent selection
    document.getElementById('thread-agent-select').addEventListener('change', loadThreadsForAgent);
});

// Load agents for the dropdown
async function loadAgentsForDropdown(selectId) {
    try {
        console.log(`Loading agents for dropdown ${selectId}...`);
        
        const selectElement = document.getElementById(selectId);
        if (!selectElement) {
            console.error(`Element with ID ${selectId} not found`);
            return;
        }
        
        selectElement.innerHTML = '<option value="">Loading agents...</option>';
        
        // Use the API utility for making the request with proper authentication
        const agents = await API.get('/agents');
        
        console.log('Agents loaded:', agents);
        
        if (agents.length === 0) {
            selectElement.innerHTML = '<option value="">No agents available</option>';
            return;
        }
        
        let options = '<option value="">Select an agent</option>';
        
        agents.forEach(agent => {
            // Use the UUID agent_id directly from the API response
            options += `<option value="${agent.agent_id}">${agent.agent_name}</option>`;
        });
        
        selectElement.innerHTML = options;
        
    } catch (error) {
        console.error('Error loading agents:', error);
        Utils.showNotification(`Error loading agents: ${error.detail || error.message || 'Unknown error'}`, 'danger');
        document.getElementById(selectId).innerHTML = '<option value="">Error loading agents</option>';
    }
}

// Load threads for the selected agent
async function loadThreadsForAgent() {
    const agentSelect = document.getElementById('thread-agent-select');
    const threadSelect = document.getElementById('thread-select');
    const agentId = agentSelect.value;
    
    // Reset and disable thread select if no agent is selected
    if (!agentId) {
        threadSelect.innerHTML = '<option value="">Select an agent first</option>';
        threadSelect.disabled = true;
        return;
    }
    
    try {
        // Show loading state
        threadSelect.innerHTML = '<option value="">Loading threads...</option>';
        threadSelect.disabled = true;
        
        // Get agent logs for the selected agent
        const response = await API.get(`/agent-logs/${agentId}`);
        console.log('Agent logs response:', response);
        
        // Handle different response formats
        let agentLogs = [];
        if (Array.isArray(response)) {
            agentLogs = response; // Direct array response
        } else if (response && response.data && Array.isArray(response.data)) {
            agentLogs = response.data; // Nested data array
        } else if (response && typeof response === 'object') {
            // Single log object
            agentLogs = [response];
        }
        
        console.log('Processed agent logs:', agentLogs);
        
        if (!agentLogs || agentLogs.length === 0) {
            threadSelect.innerHTML = '<option value="">No threads available</option>';
            threadSelect.disabled = true;
            return;
        }
        
        // Create options for each thread
        let options = '<option value="">Select a thread</option>';
        
        // Process each log
        agentLogs.forEach(log => {
            // Check if log is valid
            if (!log) return;
            
            // Format the date for better display
            const dateStr = log.created_at || log.date;
            const date = dateStr ? new Date(dateStr) : new Date();
            const formattedDate = date.toLocaleString();
            
            // Use thread_id if available, fallback to 1
            const threadId = log.thread_id || '1';
            const logId = log.agent_log_id;
            
            if (logId) {
                options += `<option value="${logId}|${threadId}">Thread ${threadId} (${formattedDate})</option>`;
            }
        });
        
        threadSelect.innerHTML = options;
        threadSelect.disabled = false;
        
    } catch (error) {
        console.error('Error loading threads:', error);
        Utils.showNotification(`Error loading threads: ${error.detail || error.message || 'Unknown error'}`, 'danger');
        threadSelect.innerHTML = '<option value="">Error loading threads</option>';
        threadSelect.disabled = true;
    }
}

// Helper function to display JSON responses
function displayJSON(elementId, data) {
    const resultElement = document.getElementById(elementId);
    resultElement.innerHTML = `
        <div class="alert alert-success">
            <h4>Response:</h4>
            <pre>${JSON.stringify(data, null, 2)}</pre>
        </div>
    `;
}

// Helper function to display errors
function displayError(elementId, error) {
    const resultElement = document.getElementById(elementId);
    resultElement.innerHTML = `
        <div class="alert alert-danger">
            <h4>Error:</h4>
            <p>${error.message || error}</p>
        </div>
    `;
}

// Helper function to make API calls - using the API utility from main.js
async function callAPI(url, method = 'GET', data = null) {
    try {
        let responseData;
        
        if (method === 'GET') {
            responseData = await API.get(url);
        } else if (method === 'POST') {
            responseData = await API.post(url, data);
        } else if (method === 'PUT') {
            responseData = await API.put(url, data);
        } else if (method === 'DELETE') {
            responseData = await API.delete(url);
        }
        
        return responseData;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Share Agent Form
document.getElementById('shareAgentForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const agentSelect = document.getElementById('agent-select');
    const agentId = agentSelect.value;
    
    if (!agentId) {
        displayError('shareAgentResult', new Error('Please select an agent'));
        return;
    }
    
    const agentName = agentSelect.options[agentSelect.selectedIndex].text;
    const isPublic = document.getElementById('isPublic').checked;
    
    try {
        // Show loading indicator
        Utils.showLoading('shareAgentResult');
        
        const data = await API.post(`/feature-sharing/agent/share-anyone-with-link/${agentId}/`, { is_public: isPublic });
        displayJSON('shareAgentResult', data);
        
        // Create a clickable link for easy testing
        const resultElement = document.getElementById('shareAgentResult');
        if (data.public_hash) {
            const linkHtml = `
                <div class="mt-3">
                    <p>Agent: <strong>${agentName}</strong> (${agentId})</p>
                    <p>Public Hash: <strong>${data.public_hash}</strong></p>
                    <p>View Agent: <a href="#" onclick="document.getElementById('agentHash').value='${data.public_hash}'; document.getElementById('viewSharedAgentForm').dispatchEvent(new Event('submit')); return false;">Test View</a></p>
                </div>
            `;
            resultElement.innerHTML += linkHtml;
        }
        
        Utils.showNotification('Agent shared successfully!', 'success');
    } catch (error) {
        displayError('shareAgentResult', error);
        Utils.showNotification(`Error sharing agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
});

// Share Thread Form
document.getElementById('shareThreadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const threadSelect = document.getElementById('thread-select');
    const threadValue = threadSelect.value;
    
    if (!threadValue) {
        displayError('shareThreadResult', new Error('Please select a thread'));
        return;
    }
    
    // Parse the thread value (format: "agentLogId|threadId")
    const [agentLogId, threadId] = threadValue.split('|');
    const threadName = threadSelect.options[threadSelect.selectedIndex].text;
    const isPublic = document.getElementById('threadIsPublic').checked;
    
    // Get the agent ID from the agent select dropdown
    const agentSelect = document.getElementById('thread-agent-select');
    const agentId = agentSelect.value;
    
    try {
        // Show loading indicator
        Utils.showLoading('shareThreadResult');
        
        const data = await API.post(`/feature-sharing/thread/share-anyone-with-link/${agentId}/${agentLogId}`, { is_public: isPublic });
        displayJSON('shareThreadResult', data);
        
        // Create a clickable link for easy testing
        const resultElement = document.getElementById('shareThreadResult');
        if (data.public_hash) {
            const linkHtml = `
                <div class="mt-3">
                    <p>Thread: <strong>${threadName}</strong></p>
                    <p>Agent ID: <strong>${agentId}</strong>, Agent Log ID: <strong>${agentLogId}</strong>, Thread ID: <strong>${threadId}</strong></p>
                    <p>Public Hash: <strong>${data.public_hash}</strong></p>
                    <p>View Thread: <a href="#" onclick="document.getElementById('threadHash').value='${data.public_hash}'; document.getElementById('viewSharedThreadForm').dispatchEvent(new Event('submit')); return false;">Test View</a></p>
                </div>
            `;
            resultElement.innerHTML += linkHtml;
        }
        
        Utils.showNotification('Thread shared successfully!', 'success');
    } catch (error) {
        displayError('shareThreadResult', error);
        Utils.showNotification(`Error sharing thread: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
});

// View Shared Agent Form
document.getElementById('viewSharedAgentForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const agentHash = document.getElementById('agentHash').value;
    
    try {
        const data = await callAPI(`/agent-invoke/shared-agent/${agentHash}`);
        displayJSON('viewSharedAgentResult', data);
    } catch (error) {
        displayError('viewSharedAgentResult', error);
    }
});

// View Shared Thread Form
document.getElementById('viewSharedThreadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const threadHash = document.getElementById('threadHash').value;
    
    try {
        const data = await callAPI(`/agent-invoke/shared-thread/${threadHash}`);
        displayJSON('viewSharedThreadResult', data);
    } catch (error) {
        displayError('viewSharedThreadResult', error);
    }
});

// Check Editor Access Form
document.getElementById('checkEditorAccessForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const agentSelect = document.getElementById('editor-agent-select');
    const agentId = agentSelect.value;
    
    if (!agentId) {
        displayError('checkEditorAccessResult', new Error('Please select an agent'));
        return;
    }
    
    const agentName = agentSelect.options[agentSelect.selectedIndex].text;
    const email = document.getElementById('editorEmail').value;
    
    if (!email) {
        displayError('checkEditorAccessResult', new Error('Please enter an email address'));
        return;
    }
    
    try {
        // Show loading indicator
        Utils.showLoading('checkEditorAccessResult');
        
        const data = await API.post(`/feature-sharing/agent/from_email/${agentId}`, { email });
        displayJSON('checkEditorAccessResult', data);
        
        // Add a helpful message about what the status means
        const resultElement = document.getElementById('checkEditorAccessResult');
        let statusMessage = '';
        
        if (data.status === 'editor') {
            statusMessage = `<div class="alert alert-success mt-3">
                <strong>Editor Access:</strong> User <strong>${email}</strong> can edit and invoke the agent <strong>${agentName}</strong>.
            </div>`;
        } else if (data.status === 'visitor') {
            statusMessage = `<div class="alert alert-info mt-3">
                <strong>Visitor Access:</strong> User <strong>${email}</strong> can view but not edit or invoke the agent <strong>${agentName}</strong>.
            </div>`;
        } else {
            statusMessage = `<div class="alert alert-warning mt-3">
                <strong>No Access:</strong> User <strong>${email}</strong> does not have any access to the agent <strong>${agentName}</strong>.
            </div>`;
        }
        
        resultElement.innerHTML += statusMessage;
    } catch (error) {
        displayError('checkEditorAccessResult', error);
        Utils.showNotification(`Error checking access: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
});
