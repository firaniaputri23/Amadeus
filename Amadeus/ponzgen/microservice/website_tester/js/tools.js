/**
 * Tools JavaScript file
 * Handles all tool-related functionality
 */

// Global variables
let currentToolId = null;
let allCompanies = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function () {
    // Check authentication
    if (!Utils.checkAuth()) return;

    // Load tools
    loadTools();

    // Load companies for filter and form
    loadCompanies();

    // Event listeners
    document.getElementById('refresh-tools').addEventListener('click', loadTools);
    document.getElementById('company-filter').addEventListener('change', loadTools);
    document.getElementById('save-tool').addEventListener('click', saveTool);
    document.getElementById('add-version-btn').addEventListener('click', addVersionField);

    // Clone tool event listeners
    document.getElementById('clone-tool-btn').addEventListener('click', showCloneToolModal);
    document.getElementById('confirm-clone-tool').addEventListener('click', cloneSelectedTool);

    // Add event listener for tool name validation
    document.getElementById('tool-name').addEventListener('blur', validateToolName);

    // Reset form when modal is opened for creating a new tool
    document.getElementById('create-tool-btn').addEventListener('click', function () {
        resetToolForm();
        document.getElementById('tool-modal-label').textContent = 'Create Tool';
    });

    // Initialize with one version field
    addVersionField();
});

// Load all tools
async function loadTools() {
    try {
        Utils.showLoading('tools-container');

        // First refresh MCP tools
        try {
            await refreshMcpTools();
            console.log('MCP tools refreshed successfully');
        } catch (refreshError) {
            console.error('Error refreshing MCP tools:', refreshError);
            // Continue loading tools even if refresh fails
        }

        const companyId = document.getElementById('company-filter').value;
        let endpoint = '/tools';

        if (companyId) {
            endpoint += `?company_id=${companyId}`;
        }

        const tools = await API.get(endpoint);

        if (tools.length === 0) {
            Utils.hideLoading('tools-container', '<p class="text-center">No tools found</p>');
            document.getElementById('stats-total').textContent = '0';
            document.getElementById('stats-active').textContent = '0';
            return;
        }

        // Update Stats
        document.getElementById('stats-total').textContent = tools.length;
        const activeCount = tools.filter(t => t.on_status === 'Online').length;
        document.getElementById('stats-active').textContent = activeCount;



        let html = '';

        tools.forEach(tool => {
            const isPredefined = tool.company_id === "95901eaa-c08d-4b0a-a5d6-3063a622cb98";
            let statusText = "OFFLINE";
            let statusColor = "var(--text-secondary)";

            if (tool.on_status === 'Online') {
                statusText = "ONLINE";
                statusColor = "var(--q-yellow)";
            } else if (tool.on_status === 'Predefined') {
                statusText = "SYSTEM";
                statusColor = "#fff";
            }

            html += `
                <div class="col">
                    <div class="tool-card h-100 d-flex flex-column" onclick="loadToolDetails('${tool.tool_id}')">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div class="tool-icon">
                                <i class="bi bi-tools"></i>
                            </div>
                            <span class="tool-status" style="color: ${statusColor}; border-color: ${statusColor};">
                                ${statusText}
                            </span>
                        </div>

                        <h3 class="tool-name mb-2">${tool.name}</h3>
                        
                        <p class="tool-desc mb-3 flex-grow-1">
                            ${tool.description || 'No description provided.'}
                        </p>
                        
                        <div class="d-flex justify-content-end gap-2 mt-auto" onclick="event.stopPropagation()">
                             <button class="btn btn-sm btn-quantum-secondary edit-tool p-1 px-2" data-id="${tool.tool_id}" title="Edit">
                                <i class="bi bi-pencil"></i>
                             </button>
                             <button class="btn btn-sm btn-quantum-secondary delete-tool p-1 px-2" style="color: #ff6b6b; border-color: #ff6b6b;" data-id="${tool.tool_id}" title="Delete">
                                <i class="bi bi-trash"></i>
                             </button>
                        </div>
                    </div>
                </div>
            `;
        });

        if (!html) html = '<div class="text-center w-100 p-5 text-secondary">No tools found matching your criteria.</div>';

        Utils.hideLoading('tools-container', html);

        // Event listeners for action buttons
        document.querySelectorAll('.edit-tool').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                editTool(btn.dataset.id);
            });
        });

        document.querySelectorAll('.delete-tool').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteTool(btn.dataset.id);
            });
        });

    } catch (error) {
        Utils.hideLoading('tools-container', `<p class="text-center text-danger">Error loading tools: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}

// Load tool details
async function loadToolDetails(toolId) {
    try {
        currentToolId = toolId;

        const detailsContainer = 'tool-details-content';
        const panel = document.getElementById('tool-details-panel');
        Utils.showLoading(detailsContainer);

        if (panel) panel.style.transform = 'translateX(0)';

        const tool = await API.get(`/tools/${toolId}`);

        // Debug log
        console.log('Received tool data:', JSON.stringify(tool, null, 2));

        let detailsHtml = `
             <div class="mb-4">
                 <div class="d-flex align-items-center mb-3">
                    <div class="icon-box bg-light text-success rounded-circle me-3" style="width: 48px; height: 48px;">
                        <i class="bi bi-tools fs-4"></i>
                    </div>
                    <div>
                        <h5 class="fw-bold mb-0 text-break">${tool.name}</h5>
                        <span class="text-xs text-muted font-monospace">${tool.tool_id}</span>
                    </div>
                </div>

                <div class="p-3 bg-light rounded border border-light mb-3">
                    <label class="text-xs fw-bold text-uppercase text-muted mb-1">Function</label>
                    <p class="text-sm mb-0">${tool.description || 'No description available.'}</p>
                </div>

                 <div class="row g-2 mb-3">
                    <div class="col-6">
                        <div class="p-2 border rounded text-center">
                            <span class="d-block text-xs text-muted">Status</span>
                            <span class="fw-bold ${tool.on_status === 'Online' ? 'text-success' : 'text-danger'}">
                                ${tool.on_status}
                            </span>
                        </div>
                    </div>
                     <div class="col-6">
                        <div class="p-2 border rounded text-center">
                            <span class="d-block text-xs text-muted">Ownership</span>
                            <span class="fw-bold text-dark">
                                ${tool.company_id ? 'Corporate' : 'Personal'}
                            </span>
                        </div>
                    </div>
                </div>
            
                <h6 class="fw-bold mt-4 mb-3 border-bottom pb-2">Version History</h6>
        `;

        if (tool.versions && tool.versions.length > 0) {
            detailsHtml += '<div class="accordion accordion-flush" id="versionsAccordion">';

            tool.versions.forEach((version, index) => {
                const releasedData = version.released || {};
                const accordionId = `version-${index}`;

                detailsHtml += `
                    <div class="accordion-item border rounded mb-2">
                        <h2 class="accordion-header">
                            <button class="accordion-button ${index > 0 ? 'collapsed' : ''} py-2 bg-light rounded" type="button" data-bs-toggle="collapse" data-bs-target="#${accordionId}">
                                <span class="fw-bold me-2">v${version.version}</span>
                                <span class="text-muted text-xs">Port: ${releasedData.port || 'Auto'}</span>
                            </button>
                        </h2>
                        <div id="${accordionId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" data-bs-parent="#versionsAccordion">
                            <div class="accordion-body p-3">
                                <div class="mb-2">
                                    <label class="text-xs fw-bold text-muted">Method</label>
                                    <div class="text-sm font-monospace bg-light p-1 rounded">${releasedData.method || 'N/A'}</div>
                                </div>
                                <div class="mb-2">
                                     <label class="text-xs fw-bold text-muted">Arguments</label>
                                     <div class="text-sm font-monospace bg-light p-1 rounded text-break">${releasedData.args || 'None'}</div>
                                </div>
                                
                                <div class="mb-2">
                                     <label class="text-xs fw-bold text-muted">Environment Config</label>
                                     <pre class="bg-dark text-white p-2 rounded text-xs mb-0" style="max-height: 100px;">${JSON.stringify(releasedData.env || {}, null, 2)}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });

            detailsHtml += '</div>'; // End accordion
        } else {
            detailsHtml += '<p class="text-muted text-sm fst-italic">No version history available.</p>';
        }

        // Add JSON representation
        detailsHtml += `
            <div class="mt-4">
                 <label class="text-xs fw-bold text-uppercase text-muted mb-2">Raw Definition</label>
                 <pre class="bg-light p-3 rounded border text-xs text-muted" style="max-height: 150px; overflow-y: auto;">${JSON.stringify(tool, null, 2)}</pre>
            </div>
        </div>`;

        Utils.hideLoading(detailsContainer, detailsHtml);

    } catch (error) {
        if (document.getElementById('tool-details-content')) {
            Utils.hideLoading('tool-details-content', `<p class="text-center text-danger">Error: ${error.detail || error.message || 'Unknown error'}</p>`);
        }
    }
}

// Format tool versions
function formatVersions(versions) {
    if (!versions || versions.length === 0) {
        return 'None';
    }

    // Debug log the versions data
    console.log('Formatting versions data:', JSON.stringify(versions, null, 2));

    // Check if versions have the expected structure
    const validVersions = versions.filter(v => v && v.version);
    if (validVersions.length === 0) {
        return 'Invalid version format';
    }

    // Format as version numbers with additional details
    return validVersions.map(v => {
        let details = '';
        if (v.released) {
            const port = v.released.port || 'N/A';
            details = ` (port: ${port})`;
        }
        return `${v.version}${details}`;
    }).join(', ');
}

// Load companies for filter and form
async function loadCompanies() {
    try {
        const companies = await API.get('/companies');
        allCompanies = companies;

        const filterSelect = document.getElementById('company-filter');
        const formSelect = document.getElementById('tool-company');

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

// Reset tool form
function resetToolForm() {
    document.getElementById('tool-form').reset();
    document.getElementById('tool-id').value = '';

    // Reset any validation state
    const toolNameInput = document.getElementById('tool-name');
    toolNameInput.classList.remove('is-invalid', 'is-valid');
    const feedbackElement = toolNameInput.nextElementSibling;
    feedbackElement.className = 'form-text text-muted';
    feedbackElement.textContent = 'Tool name must be unique. Duplicate names are not allowed.';

    // Set active checkbox to checked by default
    document.getElementById('tool-active').checked = true;

    // Clear versions container and add one empty version
    const versionsContainer = document.getElementById('versions-container');
    versionsContainer.innerHTML = '';
    addVersionField();
}

// Add version field to form
function addVersionField(version = { version: '1.0.0', released: { env: {}, args: '', method: 'sse', required_env: [] } }) {
    const versionsContainer = document.getElementById('versions-container');
    const versionIndex = versionsContainer.children.length;

    // Ensure released is an object with the correct structure
    let releasedData = version.released;
    if (!releasedData || typeof releasedData !== 'object') {
        try {
            // Try to parse it as JSON if it's a string
            if (typeof releasedData === 'string') {
                releasedData = JSON.parse(releasedData);
            } else {
                // Default structure
                releasedData = { env: {}, args: '', method: 'sse', required_env: [] };
            }
        } catch (e) {
            // If parsing fails, use default structure
            releasedData = { env: {}, args: '', method: 'sse', required_env: [] };
        }
    }

    // Convert env and required_env to strings for display
    const envJson = JSON.stringify(releasedData.env || {}, null, 2);
    const requiredEnvJson = JSON.stringify(releasedData.required_env || [], null, 2);

    const versionDiv = document.createElement('div');
    versionDiv.className = 'card mb-3 version-row border-secondary bg-transparent';
    versionDiv.innerHTML = `
        <div class="card-header d-flex justify-content-between align-items-center border-secondary bg-dark bg-opacity-50">
            <h6 class="mb-0 text-white"><i class="bi bi-layers me-2" style="color: var(--q-magenta);"></i>Version Iteration</h6>
            <button type="button" class="btn btn-sm btn-outline-danger remove-version border-0"><i class="bi bi-trash"></i></button>
        </div>
        <div class="card-body">
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Version Number</label>
                    <input type="text" class="form-control bg-dark text-white border-secondary version-number" placeholder="e.g., 1.0.0" value="${version.version || '1.0.0'}">
                </div>
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Method</label>
                    <input type="text" class="form-control bg-dark text-white border-secondary version-method" value="sse" readonly>
                    <small class="form-text text-white-50" style="font-size: 0.7rem;">Currently only SSE is supported</small>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Args</label>
                    <input type="text" class="form-control bg-dark text-white border-secondary version-args" placeholder="Command arguments" value="${releasedData.args || ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Port</label>
                    <input type="text" class="form-control bg-dark text-white-50 border-secondary version-port" placeholder="Port number" value="${releasedData.port || 'Auto-assigned by System'}" disabled>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Env Vars (JSON)</label>
                    <textarea class="form-control bg-dark text-white border-secondary version-env" rows="4" placeholder='{"API_KEY": "..."}'>${envJson}</textarea>
                    <small class="form-text opacity-75" style="font-size: 0.7rem; color: var(--q-magenta);">* Enter as valid JSON object</small>
                </div>
                <div class="col-md-6">
                    <label class="form-label text-white-50 small text-uppercase">Required Env (JSON Array)</label>
                    <textarea class="form-control bg-dark text-white border-secondary version-required-env" rows="4" placeholder='["API_KEY"]'>${requiredEnvJson}</textarea>
                    <small class="form-text opacity-75" style="font-size: 0.7rem; color: var(--q-magenta);">* Enter as valid JSON array</small>
                </div>
            </div>
        </div>
    `;

    versionsContainer.appendChild(versionDiv);

    // Add event listener to remove button
    versionDiv.querySelector('.remove-version').addEventListener('click', function () {
        versionDiv.remove();
    });
}

// Save tool (create or update)
async function saveTool() {
    try {
        const toolId = document.getElementById('tool-id').value;
        const isUpdate = !!toolId;

        // Get form values
        const toolName = document.getElementById('tool-name').value;
        const description = document.getElementById('tool-description').value;
        const companyId = document.getElementById('tool-company').value;
        const isActive = document.getElementById('tool-active').checked;

        // Set on_status based on active checkbox
        const onStatus = isActive ? "Online" : "Offline";

        // Debug log for the active state and resulting status
        console.log(`Tool active checkbox state: ${isActive}`);
        console.log(`Setting on_status to: ${onStatus}`);

        // Get versions
        const versionRows = document.querySelectorAll('.version-row');
        const versions = [];

        // Validate form
        if (!toolName) {
            Utils.showNotification('Tool name is required', 'warning');
            return;
        }

        if (versionRows.length === 0) {
            Utils.showNotification('At least one version is required', 'warning');
            return;
        }

        // Check if a tool with the same name already exists
        try {
            // Construct the API endpoint for checking name
            let checkEndpoint = `/tools/check-name/${encodeURIComponent(toolName)}`;
            if (isUpdate) {
                checkEndpoint += `?tool_id=${toolId}`;
            }

            // Make the API call
            const nameCheckResponse = await API.get(checkEndpoint);

            // If the name exists, show a warning and return
            if (nameCheckResponse.exists) {
                Utils.showNotification('A tool with this name already exists', 'warning');
                return;
            }
        } catch (checkError) {
            console.error('Error checking tool name:', checkError);
            // Continue with the save operation even if the check fails
        }

        // Process each version
        for (let i = 0; i < versionRows.length; i++) {
            const row = versionRows[i];
            const versionNumber = row.querySelector('.version-number').value;
            // Method is fixed to 'sse' for now
            const versionMethod = 'sse';
            const versionArgs = row.querySelector('.version-args').value;
            let versionPort = row.querySelector('.version-port').value;
            const versionEnvText = row.querySelector('.version-env').value;
            const versionRequiredEnvText = row.querySelector('.version-required-env').value;

            if (!versionNumber) {
                Utils.showNotification('Version number is required for all versions', 'warning');
                throw new Error('Version number is required');
            }

            // Handle port values based on tool status
            if (isActive) {
                // For active tools with empty ports, set to empty string to trigger port assignment in the backend
                if (versionPort === 'The port number will be assigned automatically.' || !versionPort) {
                    console.log(`Tool is active with empty port for version ${versionNumber}. Backend will assign a port.`);
                    versionPort = ""; // Set to empty string to trigger port assignment in the backend
                }
            } else {
                // For inactive tools, we should always set the port to empty string
                console.log(`Tool is inactive, setting empty port for version ${versionNumber}`);
                versionPort = "";
            }

            // Parse environment variables JSON
            let envData = {};
            try {
                envData = JSON.parse(versionEnvText);
                if (typeof envData !== 'object' || envData === null || Array.isArray(envData)) {
                    throw new Error('Environment variables must be a JSON object');
                }
            } catch (e) {
                console.error('Invalid JSON for environment variables:', e);
                Utils.showNotification('Invalid JSON format for environment variables', 'warning');
                throw new Error('Invalid JSON format for environment variables');
            }

            // Parse required environment variables JSON
            let requiredEnvData = [];
            try {
                requiredEnvData = JSON.parse(versionRequiredEnvText);
                if (!Array.isArray(requiredEnvData)) {
                    throw new Error('Required environment variables must be a JSON array');
                }
            } catch (e) {
                console.error('Invalid JSON for required environment variables:', e);
                Utils.showNotification('Invalid JSON format for required environment variables', 'warning');
                throw new Error('Invalid JSON format for required environment variables');
            }

            // Create released object according to the backend model
            const releasedData = {
                env: envData,
                args: versionArgs,
                port: versionPort,
                method: versionMethod,
                required_env: requiredEnvData
            };

            // Add the version to the array
            const versionEntry = {
                version: versionNumber,
                released: releasedData
            };

            console.log(`Adding version entry:`, versionEntry);
            versions.push(versionEntry);
        }

        // Create tool data object
        const toolData = {
            name: toolName,
            description: description,
            versions: versions,
            company_id: companyId || null,
            on_status: onStatus
        };

        // Debug log
        console.log('Sending tool data:', JSON.stringify(toolData, null, 2));

        let response;
        let endpoint = '/tools';

        if (isUpdate) {
            // Update existing tool
            response = await API.put(`/tools/${toolId}${companyId ? `?company_id=${companyId}` : ''}`, toolData);
            console.log('Tool update response:', response);
            Utils.showNotification('Tool updated successfully');
        } else {
            // Create new tool
            response = await API.post(endpoint, toolData);
            console.log('Tool creation response:', response);
            Utils.showNotification('Tool created successfully');
        }

        // Refresh MCP tools after creating/updating a tool - this will assign ports to any empty port fields
        try {
            const refreshResponse = await refreshMcpTools();
            console.log('MCP tools refreshed successfully:', refreshResponse);

            // If the tool is active and we're updating, we might need to reload the tool to see the assigned port
            if (isActive && isUpdate) {
                if (refreshResponse && refreshResponse.data && refreshResponse.data.tools_updated_in_supabase > 0) {
                    console.log('Tools were updated in Supabase during refresh, reloading details');
                    // Reload the tool details to show the newly assigned port
                    if (currentToolId === toolId) {
                        loadToolDetails(toolId);
                    }
                }
            }
        } catch (refreshError) {
            console.error('Error refreshing MCP tools:', refreshError);
            // Don't show notification for this error as it's not critical to the user experience
        }

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('tool-modal'));
        modal.hide();

        // Reload tools
        loadTools();

    } catch (error) {
        console.error('Error saving tool:', error);
        Utils.showNotification(`Error saving tool: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Edit tool
async function editTool(toolId) {
    try {
        const tool = await API.get(`/tools/${toolId}`);

        // Set form values
        document.getElementById('tool-id').value = tool.tool_id;
        document.getElementById('tool-name').value = tool.name;
        document.getElementById('tool-description').value = tool.description || '';
        document.getElementById('tool-company').value = tool.company_id || '';

        // Set active checkbox based on tool status
        const isActive = tool.on_status !== "Offline";
        document.getElementById('tool-active').checked = isActive;

        // Clear versions container
        const versionsContainer = document.getElementById('versions-container');
        versionsContainer.innerHTML = '';

        // Add version fields
        if (tool.versions && tool.versions.length > 0) {
            tool.versions.forEach(version => {
                addVersionField(version);
            });
        } else {
            addVersionField();
        }

        // Update modal title
        document.getElementById('tool-modal-label').textContent = 'Edit Tool';

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('tool-modal'));
        modal.show();

    } catch (error) {
        Utils.showNotification(`Error loading tool for editing: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Refresh MCP tools
async function refreshMcpTools() {
    // return API.post('/mcp-tools/refresh', {});
    return API.get('/mcp-tools/refresh');
}

// Delete tool
async function deleteTool(toolId) {
    if (!confirm('Are you sure you want to delete this tool?')) {
        return;
    }

    try {
        await API.delete(`/tools/${toolId}`);
        Utils.showNotification('Tool deleted successfully');

        // Refresh MCP tools after deleting a tool
        try {
            await refreshMcpTools();
            console.log('MCP tools refreshed successfully');
        } catch (refreshError) {
            console.error('Error refreshing MCP tools:', refreshError);
        }

        // Reload tools
        loadTools();

        // If we were viewing the tool that was deleted, clear the details
        if (currentToolId === toolId) {
            currentToolId = null;
            document.getElementById('tool-details-container').innerHTML = '<p class="text-center">Select a tool to view details</p>';
        }

    } catch (error) {
        Utils.showNotification(`Error deleting tool: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Real-time validation of tool name
async function validateToolName() {
    const toolNameInput = document.getElementById('tool-name');
    const toolName = toolNameInput.value.trim();
    const toolId = document.getElementById('tool-id').value;
    const feedbackElement = toolNameInput.nextElementSibling;

    // Clear any previous validation styling
    toolNameInput.classList.remove('is-invalid', 'is-valid');

    // Skip validation if the name is empty
    if (!toolName) {
        return;
    }

    try {
        // Construct the API endpoint for checking name
        let checkEndpoint = `/tools/check-name/${encodeURIComponent(toolName)}`;
        if (toolId) {
            checkEndpoint += `?tool_id=${toolId}`;
        }

        // Make the API call
        const nameCheckResponse = await API.get(checkEndpoint);

        // Update the UI based on the response
        if (nameCheckResponse.exists) {
            toolNameInput.classList.add('is-invalid');
            feedbackElement.className = 'form-text text-danger';
            feedbackElement.textContent = 'This tool name is already in use. Please choose another name.';
        } else {
            toolNameInput.classList.add('is-valid');
            feedbackElement.className = 'form-text text-muted';
            feedbackElement.textContent = 'Tool name must be unique. Duplicate names are not allowed.';
        }
    } catch (error) {
        console.error('Error validating tool name:', error);
        // Reset to default state if validation fails
        feedbackElement.className = 'form-text text-muted';
        feedbackElement.textContent = 'Tool name must be unique. Duplicate names are not allowed.';
    }
}

// Show clone tool modal
async function showCloneToolModal() {
    try {
        // Show loading
        Utils.showLoading('clone-tools-container');

        // Get all tools the user has access to
        const companyId = document.getElementById('company-filter').value;
        let endpoint = '/tools';

        const tools = await API.get(endpoint);

        if (tools.length === 0) {
            Utils.hideLoading('clone-tools-container', '<p class="text-center">No tools found</p>');
            document.getElementById('confirm-clone-tool').disabled = true;
            return;
        }

        let html = '';

        tools.forEach(tool => {
            // Check if tool belongs to the Predefined company
            const isPredefined = tool.company_id === "95901eaa-c08d-4b0a-a5d6-3063a622cb98";
            let statusText = "Inactive";

            if (tool.on_status === 'Online') {
                statusText = "Online";
            } else if (tool.on_status === 'Predefined') {
                statusText = "Predefined";
            } else if (tool.on_status === 'Offline') {
                statusText = "Offline";
            }

            const companyLabel = tool.company_id ? 'Organization' : 'Personal';

            html += `
                 <div class="col-md-6 col-lg-4 mb-3">
                     <div class="management-card h-100 d-flex flex-column cursor-pointer" data-id="${tool.tool_id}" onclick="selectToolToClone(this)">
                        <div class="d-flex align-items-center mb-3">
                            <div class="icon-box bg-light text-primary rounded-circle me-3" style="width: 40px; height: 40px;">
                                <i class="bi bi-tools fs-5"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-0 text-dark">${tool.name}</h6>
                                <span class="badge bg-light text-secondary border rounded-pill fw-normal" style="font-size: 0.7rem;">${companyLabel}</span>
                            </div>
                        </div>
                        <p class="text-muted text-xs mb-0 text-truncate">${tool.description || 'No description'}</p>
                     </div>
                 </div>
            `;
        });

        if (!html) html = '<p class="text-muted text-center w-100">No tools found for cloning.</p>';
        else html = '<div class="row">' + html + '</div>';

        Utils.hideLoading('clone-tools-container', html);

        // Add click logic via global function or event delegation (handled by onclick above for simplicity in modal)


        Utils.hideLoading('clone-tools-container', html);

        // Add click event listeners to tool cards
        document.querySelectorAll('#clone-tools-container .tool-card').forEach(card => {
            card.addEventListener('click', function () {
                selectToolToClone(this);
            });
        });

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('clone-tool-modal'));
        modal.show();

    } catch (error) {
        Utils.hideLoading('clone-tools-container', `<p class="text-center text-danger">Error loading tools: ${error.detail || error.message || 'Unknown error'}</p>`);
        Utils.showNotification(`Error loading tools: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Select tool to clone
function selectToolToClone(element) {
    // Clear previous selection
    document.querySelectorAll('#clone-tools-container .tool-card').forEach(card => {
        card.classList.remove('border-primary');
    });

    // Add border to selected tool
    element.classList.add('border-primary');

    // Enable confirm button
    document.getElementById('confirm-clone-tool').disabled = false;

    // Store the selected tool ID as a data attribute on the confirm button
    document.getElementById('confirm-clone-tool').setAttribute('data-tool-id', element.getAttribute('data-id'));
}

// Clone selected tool
async function cloneSelectedTool() {
    const toolId = document.getElementById('confirm-clone-tool').getAttribute('data-tool-id');

    if (!toolId) {
        Utils.showNotification('Please select a tool to clone', 'warning');
        return;
    }

    try {
        // Show loading notification
        Utils.showNotification('Cloning tool...', 'info');

        // Call the server endpoint to clone the tool
        const response = await API.post(`/tools/${toolId}/clone`);

        Utils.showNotification('Tool cloned successfully');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('clone-tool-modal'));
        modal.hide();

        // Reload tools
        loadTools();

        // Load the newly cloned tool details
        loadToolDetails(response.tool_id);

    } catch (error) {
        Utils.showNotification(`Error cloning tool: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}