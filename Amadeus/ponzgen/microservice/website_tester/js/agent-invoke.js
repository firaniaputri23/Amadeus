/**
 * Agent Invoke JavaScript file
 * Handles agent invocation functionality
 */

// Use the API utility to get the base URL
function getInvokeApiUrl() {
    // For backward compatibility, use API.getBaseUrl() instead of a separate URL
    return API.getBaseUrl();
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Load agents for the dropdown
    loadAgentsForDropdown();
    
    // Load available LLM models
    loadAvailableModels();
    
    // Event listeners
    document.getElementById('agent-select').addEventListener('change', updateAgentSelection);
    document.getElementById('get-agent-info').addEventListener('click', getAgentInfo);
    document.getElementById('invoke-agent').addEventListener('click', invokeAgent);
});

// Load available LLM models from the API
async function loadAvailableModels() {
    const modelSelect = document.getElementById('model-name');
    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    
    try {
        console.log('Loading available VLM models...');
        
        // Fetch available models from the API
        const response = await API.get('/get-llms');
        
        // Always use the custom VLM model as specified in get_llms.py
        const vlmModel = 'custom-vlm';
        
        // Clear and set the model select
        modelSelect.innerHTML = '';
        const option = document.createElement('option');
        option.value = vlmModel;
        option.textContent = 'Custom VLM (Gemma-2 + CLIP)';
        option.selected = true; // Set as default
        modelSelect.appendChild(option);
        
        console.log('Loaded VLM model:', vlmModel);
        
    } catch (error) {
        console.error('Error loading VLM model:', error);
        // Fallback to just showing the VLM model name even if API call fails
        modelSelect.innerHTML = `
            <option value="custom-vlm" selected>Custom VLM (Gemma-2 + CLIP)</option>
        `;
        Utils.showNotification('Using default VLM model. Could not verify available models from server.', 'warning');
    }
}

// Load agents for the dropdown
async function loadAgentsForDropdown() {
    try {
        console.log('Loading agents for dropdown...');
        console.log('Headers:', API.getHeaders(false));
        
        // Use the API utility for making the request with proper authentication
        const agents = await API.get('/agents');
        
        console.log('Agents loaded:', agents);
        
        if (agents.length === 0) {
            document.getElementById('agent-select').innerHTML = '<option value="">No agents available</option>';
            return;
        }
        
        let options = '<option value="">Select an agent</option>';
        
        agents.forEach(agent => {
            options += `<option value="${agent.agent_id}">${agent.agent_name}</option>`;
        });
        
        document.getElementById('agent-select').innerHTML = options;
        
    } catch (error) {
        Utils.showNotification(`Error loading agents: ${error.detail || error.message || 'Unknown error'}`, 'danger');
        document.getElementById('agent-select').innerHTML = '<option value="">Error loading agents</option>';
    }
}

// Current agent details stored globally
let currentAgentDetails = null;

// Update agent selection when an agent is selected
function updateAgentSelection() {
    const select = document.getElementById('agent-select');
    
    if (select.value) {
        // Get agent details when an agent is selected
        getAgentDetails(select.value);
    } else {
        // Clear agent details
        currentAgentDetails = null;
        Utils.hideLoading('agent-info-container', '<p class="text-center">Select an agent to view details</p>');
    }
}

// Get agent details using agent_id
async function getAgentDetails(agentId) {
    if (!agentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('agent-info-container');
        
        console.log(`Getting agent details for agent ID: ${agentId}`);
        console.log('Headers:', API.getHeaders(false));
        
        // Use the API utility for making the request with proper authentication
        // This uses the agent/{agent_id} endpoint as specified
        const agentDetails = await API.get(`/agents/${agentId}`);
        
        // Store agent details globally for use in invoke function
        currentAgentDetails = agentDetails;
        
        // Display agent details
        let infoHtml = `
            <div class="alert alert-info">
                <h5>${agentDetails.agent_name}</h5>
                <p>${agentDetails.description || 'No description'}</p>
                <p><strong>Style:</strong> ${agentDetails.agent_style || 'Default'}</p>
                <p><strong>Status:</strong> 
                    <span class="badge ${agentDetails.on_status ? 'bg-success' : 'bg-danger'}">
                        ${agentDetails.on_status ? 'Active' : 'Inactive'}
                    </span>
                </p>
                <p><strong>Tools:</strong> ${agentDetails.tools ? agentDetails.tools.length : 0} tools available</p>
            </div>
        `;
        
        // Add tool details if available
        if (agentDetails.tool_details && agentDetails.tool_details.length > 0) {
            infoHtml += '<h6 class="mt-3">Tool Details:</h6><ul class="list-group">';
            agentDetails.tool_details.forEach(tool => {
                infoHtml += `
                    <li class="list-group-item">
                        <strong>${tool.name}</strong> - ${tool.description || 'No description'}
                    </li>
                `;
            });
            infoHtml += '</ul>';
        }
        
        Utils.hideLoading('agent-info-container', infoHtml);
        
    } catch (error) {
        Utils.hideLoading('agent-info-container', `
            <div class="alert alert-danger">
                Error getting agent details: ${error.detail || error.message || 'Unknown error'}
            </div>
        `);
        currentAgentDetails = null;
    }
}

// Get agent info button handler (now uses the stored agent details)
async function getAgentInfo() {
    const select = document.getElementById('agent-select');
    if (!select.value) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }
    
    // If we already have the agent details, just display them again
    if (currentAgentDetails) {
        // Display the stored agent details
        let infoHtml = `
            <div class="alert alert-info">
                <h5>${currentAgentDetails.agent_name}</h5>
                <p>${currentAgentDetails.description || 'No description'}</p>
                <p><strong>Style:</strong> ${currentAgentDetails.agent_style || 'Default'}</p>
                <p><strong>Status:</strong> 
                    <span class="badge ${currentAgentDetails.on_status ? 'bg-success' : 'bg-danger'}">
                        ${currentAgentDetails.on_status ? 'Active' : 'Inactive'}
                    </span>
                </p>
                <p><strong>Tools:</strong> ${currentAgentDetails.tools ? currentAgentDetails.tools.length : 0} tools available</p>
            </div>
        `;
        
        Utils.hideLoading('agent-info-container', infoHtml);
    } else {
        // Get the agent details if we don't have them
        getAgentDetails(select.value);
    }
}

// Invoke agent
async function invokeAgent() {
    const select = document.getElementById('agent-select');
    const agentId = select.value;
    
    if (!agentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }
    
    const message = document.getElementById('agent-message').value.trim();
    
    if (!message) {
        Utils.showNotification('Please enter a message', 'warning');
        return;
    }
    
    // If we don't have agent details, get them first
    if (!currentAgentDetails) {
        try {
            await getAgentDetails(agentId);
        } catch (error) {
            Utils.showNotification('Failed to get agent details. Please try again.', 'danger');
            return;
        }
    }
    
    // Prepare request body
    const requestBody = {
        input: {
            messages: message,
            context: document.getElementById('agent-context').value
        },
        config: {
            configurable: {}
        },
        metadata: {
            model_name: document.getElementById('model-name').value,
            reset_memory: document.getElementById('reset-memory').checked,
            load_from_json: document.getElementById('load-from-json').checked,
            agent_style: document.getElementById('agent-style').value
        },
        agent_config: currentAgentDetails // Add the agent details to the request
    };
    
    // Add thread_id (required, default to "1" if empty)
    let threadId = document.getElementById('thread-id').value.trim();
    if (!threadId) {
        threadId = "1";
        document.getElementById('thread-id').value = threadId;
    }
    requestBody.config.configurable.thread_id = threadId;
    
    try {
        // Update request details
        document.getElementById('request-url').textContent = `${API.getBaseUrl()}/agent-invoke/${agentId}/invoke`;
        document.getElementById('request-headers').textContent = JSON.stringify(API.getHeaders(), null, 2);
        document.getElementById('request-body').textContent = JSON.stringify(requestBody, null, 2);
        
        // Show loading
        Utils.showLoading('response-container');
        
        console.log(`Invoking agent with agent ID: ${agentId}`);
        console.log('Request body:', requestBody);
        
        // Use the API utility for making the request with proper authentication
        // Now using agent_id in the payload instead of in the URL path
        const responseData = await API.post(`/agent-invoke/${agentId}/invoke`, requestBody);
        
        
        // Format and display the response
        let responseHtml = '';
        
        if (typeof responseData === 'object') {
            responseHtml = `<pre class="bg-light p-3 rounded">${JSON.stringify(responseData, null, 2)}</pre>`;
        } else {
            responseHtml = `<div class="p-3 bg-light rounded">${responseData}</div>`;
        }
        
        Utils.hideLoading('response-container', responseHtml);
        Utils.showNotification('Agent invoked successfully', 'success');
        
    } catch (error) {
        Utils.hideLoading('response-container', `
            <div class="alert alert-danger">
                <h5>Error invoking agent</h5>
                <p>${error.detail || error.message || 'Unknown error'}</p>
            </div>
        `);
        Utils.showNotification(`Error invoking agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}
