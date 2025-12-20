/**
 * Agents JavaScript file
 * Handles all agent-related functionality
 */

// Global variables
let currentAgentId = null;
let allTools = [];
let allCompanies = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function () {
    // Check authentication
    if (!Utils.checkAuth()) return;

    // Load agents
    loadAgents();

    // Load companies for filter and form
    loadCompanies();

    // Load tools for form
    loadTools();

    // Event listeners
    document.getElementById('refresh-agents').addEventListener('click', loadAgents);
    document.getElementById('company-filter').addEventListener('change', loadAgents);
    document.getElementById('save-agent').addEventListener('click', saveAgent);
    document.getElementById('add-tool-btn').addEventListener('click', showAddToolModal);
    document.getElementById('confirm-add-tool').addEventListener('click', addToolToAgent);
    // autofill-style-btn now uses inline onclick handler

    // Clone agent event listeners
    document.getElementById('clone-agent-btn').addEventListener('click', showCloneAgentModal);
    document.getElementById('confirm-clone').addEventListener('click', cloneSelectedAgent);

    // Reset form when modal is opened for creating a new agent
    document.getElementById('create-agent-btn').addEventListener('click', function () {
        resetAgentForm();
        document.getElementById('agent-modal-label').textContent = 'Create Agent';
    });

    // Reset the company dropdown to "Personal Agent" (the first option)
    document.getElementById('agent-modal').addEventListener('show.bs.modal', function (event) {
        const companySelect = document.getElementById('agent-company');
        companySelect.selectedIndex = 0;
        loadTools();
    });
});

// Load all agents
async function loadAgents() {
    try {
        Utils.showLoading('agents-container');

        const companyId = document.getElementById('company-filter').value;
        let endpoint = '/agents';

        if (companyId) {
            endpoint += `?company_id=${companyId}`;
        }

        const agents = await API.get(endpoint);

        if (agents.length === 0) {
            Utils.hideLoading('agents-container', '<p class="text-center">No agents found</p>');
            document.getElementById('stats-total').textContent = '0';
            document.getElementById('stats-active').textContent = '0';
            return;
        }

        // Update Stats
        document.getElementById('stats-total').textContent = agents.length;
        const activeCount = agents.filter(a => a.on_status).length;
        document.getElementById('stats-active').textContent = activeCount;

        let html = '';

        agents.forEach(agent => {
            const statusClass = agent.on_status ? 'active' : 'inactive';
            const statusText = agent.on_status ? 'ONLINE' : 'OFFLINE';
            const statusColor = agent.on_status ? 'var(--q-cyan)' : 'var(--text-secondary)';
            const statusBorder = agent.on_status ? 'var(--q-cyan)' : 'var(--text-secondary)';

            html += `
                <div class="col">
                    <div class="agent-card h-100 d-flex flex-column" onclick="loadAgentDetails('${agent.agent_id}')">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div class="agent-icon">
                                <i class="bi bi-robot"></i>
                            </div>
                            <span class="agent-status" style="color: ${statusColor}; border-color: ${statusBorder};">
                                ${statusText}
                            </span>
                        </div>

                        <h3 class="agent-name text-white mb-2">${agent.agent_name}</h3>
                        
                        <p class="agent-desc mb-3 flex-grow-1">
                            ${agent.description || 'No description provided.'}
                        </p>
                        
                        <div class="d-flex justify-content-end gap-2 mt-auto" onclick="event.stopPropagation()">
                             <button class="btn btn-sm btn-quantum-secondary edit-agent p-1 px-2" data-id="${agent.agent_id}" title="Edit">
                                <i class="bi bi-pencil"></i>
                             </button>
                             <button class="btn btn-sm btn-quantum-secondary delete-agent p-1 px-2" style="color: #ff6b6b; border-color: #ff6b6b;" data-id="${agent.agent_id}" title="Delete">
                                <i class="bi bi-trash"></i>
                             </button>
                        </div>
                    </div>
                </div>
            `;
        });

        Utils.hideLoading('agents-container', html);

        // Event listeners for action buttons (Edit/Delete)
        document.querySelectorAll('.edit-agent').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click
                editAgent(btn.dataset.id);
            });
        });

        document.querySelectorAll('.delete-agent').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent card click
                deleteAgent(btn.dataset.id);
            });
        });

    } catch (error) {
        Utils.hideLoading('agents-container', `<p class="text-center text-danger">Error loading agents: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}

// Load agent details
async function loadAgentDetails(agentId) {
    try {
        currentAgentId = agentId;

        // In new design, details go into the side panel
        const detailsContainer = 'agent-details-content';
        const panel = document.getElementById('agent-details-panel');

        Utils.showLoading(detailsContainer);
        // Utils.showLoading('agent-tools-container'); // This is now inside the panel, we'll handle it

        // Open the panel
        if (panel) panel.style.transform = 'translateX(0)';

        // Enable the add tool button (it's in the header now, but we can hook it up or add a button in the panel)
        // document.getElementById('add-tool-btn').disabled = false;

        const agent = await API.get(`/agents/${agentId}`);

        let detailsHtml = `
            <div class="mb-4">
                 <div class="d-flex align-items-center mb-3">
                    <div class="icon-box bg-dark text-white rounded-circle me-3" style="width: 48px; height: 48px; border: 1px solid var(--q-cyan); display: flex; align-items: center; justify-content: center;">
                        <i class="bi bi-robot fs-4" style="color: var(--q-cyan); text-shadow: 0 0 10px var(--q-cyan);"></i>
                    </div>
                    <div>
                        <h5 class="fw-bold mb-0 text-white">${agent.agent_name}</h5>
                        <span class="text-xs text-secondary font-monospace" style="opacity: 0.6;">${agent.agent_id}</span>
                    </div>
                </div>
                
                <div class="p-3 bg-dark bg-opacity-50 rounded border border-secondary mb-3">
                    <label class="text-xs fw-bold text-uppercase text-secondary mb-1" style="font-size: 0.7rem; letter-spacing: 1px;">Description</label>
                    <p class="text-sm mb-0 text-white">${agent.description || 'No description available.'}</p>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <div class="p-2 border border-secondary rounded text-center bg-dark bg-opacity-25">
                            <span class="d-block text-xs text-secondary" style="font-size: 0.65rem; text-transform: uppercase;">Status</span>
                            <span class="fw-bold" style="color: ${agent.on_status ? 'var(--q-cyan)' : 'var(--text-secondary)'};">
                                ${agent.on_status ? 'Active' : 'Inactive'}
                            </span>
                        </div>
                    </div>
                     <div class="col-6">
                        <div class="p-2 border border-secondary rounded text-center bg-dark bg-opacity-25">
                            <span class="d-block text-xs text-secondary" style="font-size: 0.65rem; text-transform: uppercase;">Scope</span>
                            <span class="fw-bold text-white">
                                ${agent.company_id ? 'Corporate' : 'Personal'}
                            </span>
                        </div>
                    </div>
                </div>

                <div class="mb-3">
                     <label class="text-xs fw-bold text-uppercase text-secondary mb-1" style="font-size: 0.7rem; letter-spacing: 1px;">Personality Profile</label>
                     <p class="text-sm text-secondary fst-italic bg-black bg-opacity-50 p-2 rounded border border-secondary">"${agent.agent_style || 'Default style'}"</p>
                </div>
                
                <div class="d-grid gap-2">
                    <button class="btn btn-quantum btn-sm add-tool-trigger" data-id="${agent.agent_id}">
                        <i class="bi bi-plus-circle me-1"></i> Assign New Tool
                    </button>
                </div>
            </div>
        `;

        Utils.hideLoading(detailsContainer, detailsHtml);

        // Add event listener for the new "Assign New Tool" button in the panel
        setTimeout(() => {
            const addToolBtn = document.querySelector('.add-tool-trigger');
            if (addToolBtn) {
                addToolBtn.addEventListener('click', showAddToolModal);
            }
        }, 100);

        // Load agent tools into the panel container
        loadAgentTools(agentId, agent.tool_details);

    } catch (error) {
        console.error(error);
        if (document.getElementById('agent-details-content')) {
            Utils.hideLoading('agent-details-content', `<p class="text-center text-danger">Error: ${error.detail || error.message || 'Unknown error'}</p>`);
        }
    }
}

// Load agent tools
function loadAgentTools(agentId, tools) {
    if (!tools || tools.length === 0) {
        Utils.hideLoading('agent-tools-container', '<p class="text-center">No tools assigned to this agent</p>');
        return;
    }

    // Updated for panel view - render as vertical list
    let toolsHtml = '<div class="d-flex flex-column gap-2">';

    tools.forEach(tool => {
        toolsHtml += `
            <div class="d-flex align-items-center justify-content-between p-2 bg-dark bg-opacity-40 border border-secondary rounded mb-2">
                <div class="d-flex align-items-center overflow-hidden">
                    <div class="icon-box bg-dark rounded me-2 border border-secondary" style="width: 32px; height: 32px; font-size: 0.9rem; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
                        <i class="bi bi-tools" style="color: var(--q-cyan);"></i>
                    </div>
                    <div class="text-truncate">
                        <h6 class="mb-0 text-sm fw-bold text-truncate text-white">${tool.name}</h6>
                        <small class="text-xs text-secondary text-truncate d-block" style="opacity: 0.7;">${tool.description || 'No description'}</small>
                    </div>
                </div>
                <button class="btn btn-link text-danger p-1 remove-tool" data-tool-id="${tool.tool_id}" title="Remove Tool">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
    });

    toolsHtml += '</div>';

    Utils.hideLoading('agent-tools-container', toolsHtml);

    // Add event listeners to remove tool buttons
    document.querySelectorAll('.remove-tool').forEach(button => {
        button.addEventListener('click', function () {
            const toolId = this.getAttribute('data-tool-id');
            removeToolFromAgent(toolId);
        });
    });
}

// Format tool versions
function formatVersions(versions) {
    if (!versions || versions.length === 0) {
        return 'None';
    }

    return versions.map(v => v.version).join(', ');
}

// Load companies for filter and form
async function loadCompanies() {
    try {
        const companies = await API.get('/companies');
        allCompanies = companies;

        const filterSelect = document.getElementById('company-filter');
        const formSelect = document.getElementById('agent-company');

        // Clear existing options (except the first one)
        while (filterSelect.options.length > 1) {
            filterSelect.remove(1);
        }

        while (formSelect.options.length > 1) {
            formSelect.remove(1);
        }

        // Add companies to selects
        companies.forEach(company => {
            const filterOption = new Option(company.name, company.company_id);
            const formOption = new Option(company.name, company.company_id);

            filterSelect.add(filterOption);
            formSelect.add(formOption);
        });

    } catch (error) {
        console.error('Error loading companies:', error);
    }
}

document.getElementById('agent-company').addEventListener('change', async function () {
    const companyId = this.value;
    await loadTools(companyId);
});

// Load tools for form
async function loadTools(companyId = null) {
    try {
        let url = '/tools';
        if (companyId && companyId !== '') {
            url += `?company_id=${companyId}`;
        }

        const tools = await API.get(url);
        allTools = tools;

        const toolsSelect = document.getElementById('agent-tools');

        // Clear existing options
        toolsSelect.innerHTML = '';

        // Add tools to select
        tools.forEach(tool => {
            const option = new Option(tool.name, tool.tool_id);
            toolsSelect.add(option);
        });

    } catch (error) {
        console.error('Error loading tools:', error);
    }
}

// Reset agent form
function resetAgentForm() {
    document.getElementById('agent-form').reset();
    document.getElementById('agent-id').value = '';

    // Clear selected tools
    const toolsSelect = document.getElementById('agent-tools');
    for (let i = 0; i < toolsSelect.options.length; i++) {
        toolsSelect.options[i].selected = false;
    }
}

// Save agent (create or update)
async function saveAgent() {
    try {
        const agentId = document.getElementById('agent-id').value;
        const isUpdate = !!agentId;

        // Get form values
        const agentName = document.getElementById('agent-name').value;
        const description = document.getElementById('agent-description').value;
        const agentStyleText = document.getElementById('agent-style').value;
        const onStatus = document.getElementById('agent-status').checked;
        const companyId = document.getElementById('agent-company').value;

        // Use agent style as normal text, with default if empty
        let agentStyle = agentStyleText.trim();
        if (!agentStyle) {
            // Use default text if the field is empty
            agentStyle = "The agent will reply in a warm and friendly manner, using English.";
        }
        console.log('Using agent style as text:', agentStyle);

        // Get selected tools
        const toolsSelect = document.getElementById('agent-tools');
        const selectedTools = Array.from(toolsSelect.selectedOptions).map(option => option.value);

        // Create agent data object
        const agentData = {
            agent_name: agentName,
            description: description,
            agent_style: agentStyle,
            on_status: onStatus,
            tools: selectedTools
        };

        // Add company_id if selected
        if (companyId) {
            agentData.company_id = companyId;
        }

        let response;

        if (isUpdate) {
            // Update existing agent
            response = await API.put(`/agents/${agentId}`, agentData);
            Utils.showNotification('Agent updated successfully');
        } else {
            // Create new agent
            response = await API.post('/agents', agentData);
            Utils.showNotification('Agent created successfully');
        }

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('agent-modal'));
        modal.hide();

        // Reload agents
        loadAgents();

        // If we were viewing the agent that was updated, reload its details
        if (isUpdate && currentAgentId === agentId) {
            loadAgentDetails(agentId);
        }

    } catch (error) {
        Utils.showNotification(`Error saving agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Edit agent
async function editAgent(agentId) {
    try {
        const agent = await API.get(`/agents/${agentId}`);

        // Set form values
        document.getElementById('agent-id').value = agent.agent_id;
        document.getElementById('agent-name').value = agent.agent_name;
        document.getElementById('agent-description').value = agent.description || '';

        // Handle agent style as normal text
        const styleInput = document.getElementById('agent-style');
        if (agent.agent_style) {
            // For backward compatibility, handle both string and object types
            if (typeof agent.agent_style === 'object') {
                // If it's somehow stored as an object, convert to a descriptive string
                try {
                    styleInput.value = JSON.stringify(agent.agent_style);
                } catch (e) {
                    styleInput.value = "The agent will reply in a warm and friendly manner, using English.";
                }
            } else {
                // Use the text as-is
                styleInput.value = agent.agent_style;
            }
        } else {
            // Default text if no style is defined
            styleInput.value = "The agent will reply in a warm and friendly manner, using English.";
        }

        document.getElementById('agent-status').checked = agent.on_status;
        document.getElementById('agent-company').value = agent.company_id || '';

        // Set selected tools
        const toolsSelect = document.getElementById('agent-tools');
        for (let i = 0; i < toolsSelect.options.length; i++) {
            const option = toolsSelect.options[i];
            option.selected = agent.tools && agent.tools.includes(option.value);
        }

        // Update modal title
        document.getElementById('agent-modal-label').textContent = 'Edit Agent';

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('agent-modal'));
        modal.show();

    } catch (error) {
        Utils.showNotification(`Error loading agent for editing: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Delete agent
async function deleteAgent(agentId) {
    if (!confirm('Are you sure you want to delete this agent?')) {
        return;
    }

    try {
        await API.delete(`/agents/${agentId}`);
        Utils.showNotification('Agent deleted successfully');

        // Reload agents
        loadAgents();

        // If we were viewing the agent that was deleted, clear the details
        if (currentAgentId === agentId) {
            currentAgentId = null;
            document.getElementById('agent-details-container').innerHTML = '<p class="text-center">Select an agent to view details</p>';
            document.getElementById('agent-tools-container').innerHTML = '<p class="text-center">Select an agent to view its tools</p>';
            document.getElementById('add-tool-btn').disabled = true;
        }

    } catch (error) {
        Utils.showNotification(`Error deleting agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Show add tool modal
function showAddToolModal() {
    if (!currentAgentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    // Get current agent tools
    const agentToolsContainer = document.getElementById('agent-tools-container');
    const toolElements = agentToolsContainer.querySelectorAll('.remove-tool');
    const currentToolIds = Array.from(toolElements).map(el => el.getAttribute('data-tool-id'));

    // Filter out tools that are already assigned to the agent
    const availableTools = allTools.filter(tool => !currentToolIds.includes(tool.tool_id));

    const availableToolsSelect = document.getElementById('available-tools');
    availableToolsSelect.innerHTML = '';

    if (availableTools.length === 0) {
        availableToolsSelect.innerHTML = '<option value="">No available tools</option>';
        document.getElementById('confirm-add-tool').disabled = true;
    } else {
        availableTools.forEach(tool => {
            const option = new Option(tool.name, tool.tool_id);
            availableToolsSelect.add(option);
        });
        document.getElementById('confirm-add-tool').disabled = false;
    }

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('add-tool-modal'));
    modal.show();
}

// Add tool to agent
async function addToolToAgent() {
    if (!currentAgentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    const toolId = document.getElementById('available-tools').value;

    if (!toolId) {
        Utils.showNotification('Please select a tool', 'warning');
        return;
    }

    try {
        await API.post(`/agents/${currentAgentId}/tools/${toolId}`);
        Utils.showNotification('Tool added to agent successfully');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('add-tool-modal'));
        modal.hide();

        // Reload agent details
        loadAgentDetails(currentAgentId);

    } catch (error) {
        Utils.showNotification(`Error adding tool to agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Remove tool from agent
async function removeToolFromAgent(toolId) {
    if (!currentAgentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    if (!confirm('Are you sure you want to remove this tool from the agent?')) {
        return;
    }

    try {
        await API.delete(`/agents/${currentAgentId}/tools/${toolId}`);
        Utils.showNotification('Tool removed from agent successfully');

        // Reload agent details
        loadAgentDetails(currentAgentId);

    } catch (error) {
        Utils.showNotification(`Error removing tool from agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Autofill agent style using the agent_field_autofill API
async function autofillAgentStyle() {
    try {
        // Get current form values to use for autofill
        const agentName = document.getElementById('agent-name').value;
        const description = document.getElementById('agent-description').value;

        // Check if we have enough information to generate a style
        if (!agentName) {
            Utils.showNotification('Please enter an agent name first', 'warning');
            return;
        }

        // Prepare the JSON field data
        const jsonField = {
            agent_name: agentName
        };

        // Add description if available
        if (description) {
            jsonField.description = description;
        }

        // Get the style textarea and its current value
        const styleTextarea = document.getElementById('agent-style');
        const originalValue = styleTextarea.value;

        // Disable the textarea during generation
        styleTextarea.disabled = true;

        try {
            // Use the API utility for consistency
            const response = await API.post('/agent-field-autofill/invoke', {
                field_name: "agent_style",
                json_field: jsonField,
                existing_field_value: originalValue
            });

            // Update the style textarea with the autofilled value
            if (response && response.autofilled_value) {
                // Simulate streaming by adding characters one by one
                let displayedText = originalValue || "";
                const newText = response.autofilled_value;

                // Function to add one character at a time
                const typeText = async (text, index) => {
                    if (index < text.length) {
                        displayedText += text[index];
                        styleTextarea.value = displayedText + "▌"; // Add cursor indicator

                        // Auto-scroll to the bottom
                        styleTextarea.scrollTop = styleTextarea.scrollHeight;

                        // Wait a small random amount of time before adding the next character
                        const delay = Math.floor(Math.random() * 30) + 10; // 10-40ms
                        await new Promise(resolve => setTimeout(resolve, delay));

                        // Continue with the next character
                        await typeText(text, index + 1);
                    } else {
                        // Finished typing
                        styleTextarea.value = displayedText;
                        Utils.showNotification('Agent style autofilled successfully');
                    }
                };

                // Determine what text to type
                let textToType = newText;

                // If the response contains the original value at the start, only type the new part
                if (originalValue && newText.startsWith(originalValue)) {
                    textToType = newText.substring(originalValue.length);
                }

                // Start typing the new text
                await typeText(textToType, 0);
            } else {
                // Restore original value if no result
                styleTextarea.value = originalValue;
                Utils.showNotification('Failed to autofill agent style', 'warning');
            }
        } catch (error) {
            // Restore original value and show error
            styleTextarea.value = originalValue;
            Utils.showNotification(`Error autofilling agent style: ${error.detail || error.message || 'Unknown error'}`, 'danger');
        } finally {
            // Re-enable the textarea
            styleTextarea.disabled = false;
        }
    } catch (error) {
        // Show error
        Utils.showNotification(`Error autofilling agent style: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}
// Show clone agent modal
async function showCloneAgentModal() {
    try {
        // Show loading
        Utils.showLoading('clone-agents-container');

        // Get all agents the user has access to
        const companyId = document.getElementById('company-filter').value;
        let endpoint = '/agents';

        if (companyId) {
            endpoint += `?company_id=${companyId}`;
        }

        const agents = await API.get(endpoint);

        if (agents.length === 0) {
            Utils.hideLoading('clone-agents-container', '<p class="text-center">No agents found</p>');
            document.getElementById('confirm-clone').disabled = true;
            return;
        }

        let html = '<div class="row">';

        agents.forEach(agent => {
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card agent-card h-100" data-id="${agent.agent_id}">
                        <div class="card-body">
                            <h5 class="card-title">${agent.agent_name}</h5>
                            <p class="card-text">${agent.description || 'No description'}</p>
                            <p class="mb-1"><small class="text-muted">Status: 
                                <span class="badge ${agent.on_status ? 'bg-success' : 'bg-danger'}">
                                    ${agent.on_status ? 'Active' : 'Inactive'}
                                </span>
                            </small></p>
                            <p class="mb-1"><small class="text-muted">Style: ${agent.agent_style || 'Default'}</small></p>
                            <p class="mb-1"><small class="text-muted">Company: ${agent.company_id ? 'Company Agent' : 'Personal Agent'}</small></p>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';

        Utils.hideLoading('clone-agents-container', html);

        // Add click event listeners to agent cards
        document.querySelectorAll('#clone-agents-container .agent-card').forEach(card => {
            card.addEventListener('click', function () {
                selectAgentToClone(this);
            });
        });

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('clone-agent-modal'));
        modal.show();

    } catch (error) {
        Utils.hideLoading('clone-agents-container', `<p class="text-center text-danger">Error loading agents: ${error.detail || error.message || 'Unknown error'}</p>`);
        Utils.showNotification(`Error loading agents: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Select agent to clone
function selectAgentToClone(element) {
    // Clear previous selection
    document.querySelectorAll('#clone-agents-container .agent-card').forEach(card => {
        card.classList.remove('border-primary');
    });

    // Add border to selected agent
    element.classList.add('border-primary');

    // Enable confirm button
    document.getElementById('confirm-clone').disabled = false;

    // Store the selected agent ID as a data attribute on the confirm button
    document.getElementById('confirm-clone').setAttribute('data-agent-id', element.getAttribute('data-id'));
}

// Clone selected agent
async function cloneSelectedAgent() {
    const agentId = document.getElementById('confirm-clone').getAttribute('data-agent-id');

    if (!agentId) {
        Utils.showNotification('Please select an agent to clone', 'warning');
        return;
    }

    try {
        // Call the server endpoint to clone the agent
        const response = await API.post(`/agents/${agentId}/clone`);

        Utils.showNotification('Agent cloned successfully');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('clone-agent-modal'));
        modal.hide();

        // Reload agents
        loadAgents();

        // Load the newly cloned agent details
        loadAgentDetails(response.agent_id);

    } catch (error) {
        Utils.showNotification(`Error cloning agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}
