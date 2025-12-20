/**
 * Tools JavaScript file
 * Handles all tool-related functionality
 */

// Base URL for API requests
const API_BASE_URL = API.getBaseUrl();
console.log('API Base URL:', API_BASE_URL);

// Global variables
let currentToolId = null;
let allCompanies = [];

// Refresh MCP tools
async function refreshMcpTools() {
    try {
        // Make a GET request to refresh tools
        const response = await API.get('/mcp-tools/refresh?force_refresh=true');
        return response;
    } catch (error) {
        console.error('Error refreshing MCP tools:', error);
        throw error;
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
        
        // Set avatar preview if available
        const avatarPreview = document.getElementById('tool-avatar-preview');
        if (tool.avatar_url) {
            avatarPreview.src = tool.avatar_url;
            avatarPreview.style.display = 'block';
        } else {
            avatarPreview.style.display = 'none';
        }
        
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

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
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
    
    // Add event listener for avatar preview
    document.getElementById('tool-avatar').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('tool-avatar-preview').style.display = 'block';
                document.getElementById('tool-avatar-preview').src = e.target.result;
            };
            reader.readAsDataURL(file);
        } else {
            document.getElementById('tool-avatar-preview').style.display = 'none';
        }
    });

    // Add event listener for tool name validation
    document.getElementById('tool-name').addEventListener('blur', validateToolName);
    
    // Reset form when modal is opened for creating a new tool
    document.getElementById('create-tool-btn').addEventListener('click', function() {
        resetToolForm();
        document.getElementById('tool-modal-label').textContent = 'Create Tool';
    });
    
    // Initialize with one version field
    addVersionField();
});

// Load all tools
const ALLOWED_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'svg']);

async function loadTools() {
    try {
        Utils.showLoading('tools-container');
        
        // Initialize avatar map
        const avatarMap = new Map();
        
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
            return;
        }
        
        // Load avatars for each tool
        try {
            const avatarPromises = tools.map(tool => {
                // Convert tool_id to string if it's an object (UUID)
                const toolId = typeof tool.tool_id === 'object' ? tool.tool_id.toString() : tool.tool_id;
                return API.get(`/api/avatars/tool/${toolId}`)
                    .then(avatar => {
                        if (avatar && avatar.avatar_url) {
                            avatarMap.set(tool.tool_id, avatar.avatar_url);
                        }
                    })
                    .catch(error => {
                        console.error(`Error loading avatar for tool ${tool.tool_id}:`, error);
                    });
            });
            
            await Promise.all(avatarPromises);
        } catch (avatarError) {
            console.error('Error loading avatars:', avatarError);
            // Continue with default behavior if avatars fail to load
        }
        

        
        let html = '<div class="row">';
        
        try {
            await Promise.all(tools.map(async (tool) => {
                // Check if tool belongs to the Predefined company
                const isPredefined = tool.company_id === "95901eaa-c08d-4b0a-a5d6-3063a622cb98";
                
                // Determine badge style and text based on status
                let badgeClass = "bg-danger";
                let badgeText = "Inactive";
                
                if (tool.on_status === 'online') {
                    badgeClass = "bg-success";
                    badgeText = "Online";
                } else if (tool.on_status === 'Predefined') {
                    badgeClass = "bg-info";
                    badgeText = "Clone to Use Predefined Tools";
                } else if (tool.on_status === 'Offline') {
                    badgeClass = "bg-warning";
                    badgeText = "Turned Off";
                }
                
                // Get avatar URL from map or use default
                const avatarUrl = avatarMap.get(tool.tool_id) || 'https://ktolhizmsfzrmmhfqvmu.supabase.co/storage/v1/object/public/agent-avatars/public/default_tool.png';
                
                // Create avatar HTML with fallbacks
                let avatarHtml = `
                    <div class="rounded-circle d-inline-flex align-items-center justify-content-center me-2" 
                         style="width: 30px; height: 30px;">
                        <img src="${avatarUrl}" 
                             alt="${tool.name} avatar" 
                             style="width: 100%; height: 100%; object-fit: cover;" 
                             onerror="this.onerror=null; this.src='https://ktolhizmsfzrmmhfqvmu.supabase.co/storage/v1/object/public/agent-avatars/public/default_tool.png';">
                    </div>`;

                html += `
                    <div class="col-md-4 mb-3">
                        <div class="card tool-card h-100 ${isPredefined ? '' : ''}" style="${isPredefined ? 'background-color: #d0d4d9;' : ''}">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-2">
                                    ${avatarHtml}
                                    <h5 class="card-title mb-0">${tool.name}</h5>
                                </div>
                                <p class="card-text">${tool.description || 'No description'}</p>
                                <p class="mb-1">
                                    <small class="text-muted">Status: 
                                        <span class="badge ${badgeClass}">
                                            ${badgeText}
                                        </span>
                                        <br>
                                        <code class="text-muted">(${tool.on_status})</code>
                                    </small>
                                </p>
                                <p class="mb-0"><small class="text-muted">Versions: ${formatVersions(tool.versions)}</small></p>
                            </div>
                            ${isPredefined ? '<div class="px-3 pb-2 pt-0"><small class="text-dark">Predefined</small></div>' : ''}
                            <div class="card-footer">
                                <button class="btn btn-sm btn-primary view-tool" data-id="${tool.tool_id}">View</button>
                                <button class="btn btn-sm btn-info edit-tool" data-id="${tool.tool_id}">Edit</button>
                                <button class="btn btn-sm btn-danger delete-tool" data-id="${tool.tool_id}">Delete</button>
                            </div>
                        </div>
                    </div>
                `;
            }));
        } catch (error) {
            console.error('Error processing tools:', error);
            // If there's an error, still show the tools with default avatars
            tools.forEach(tool => {
                const isPredefined = tool.company_id === "95901eaa-c08d-4b0a-a5d6-3063a622cb98";
                const avatarUrl = avatarMap.get(tool.tool_id) || 'https://ktolhizmsfzrmmhfqvmu.supabase.co/storage/v1/object/public/agent-avatars/public/default_tool.png';

                html += `
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header d-flex align-items-center">
                                ${avatarHtml}
                                <h5 class="card-title mb-0">${tool.name}</h5>
                                <span class="badge ${badgeClass} ms-auto">${badgeText}</span>
                            </div>
                            <div class="card-body">
                                <p class="card-text">${tool.description || 'No description'}</p>
                                <p class="mb-2"><strong>Tool ID:</strong> ${tool.tool_id}</p>
                                <p class="mb-2"><strong>User ID:</strong> ${tool.user_id}</p>
                                <p class="mb-2"><strong>Company ID:</strong> ${tool.company_id || 'Personal Tool'}</p>
                                <p class="mb-2"><strong>Created:</strong> ${new Date(tool.created_at).toLocaleString()}</p>
                                <p class="mb-2"><strong>Updated:</strong> ${new Date(tool.updated_at).toLocaleString()}</p>
                                <p class="mb-2"><strong>On Status:</strong> ${tool.on_status || 'Inactive'}</p>
                                <p class="mb-2"><strong>Versions:</strong> ${formatVersions(tool.versions || [])}</p>
                                <div class="d-flex justify-content-end">
                                    <button class="btn btn-sm btn-primary me-2 view-tool" data-id="${tool.tool_id}">View</button>
                                    <button class="btn btn-sm btn-warning me-2 edit-tool" data-id="${tool.tool_id}">Edit</button>
                                    <button class="btn btn-sm btn-danger delete-tool" data-id="${tool.tool_id}">Delete</button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        html += '</div>';
        
        Utils.hideLoading('tools-container', html);
        
        // Add event listeners to buttons
        document.querySelectorAll('.view-tool').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const toolId = button.dataset.id;
                await loadToolDetails(toolId);
            });
        });
        
        document.querySelectorAll('.edit-tool').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const toolId = button.dataset.id;
                await editTool(toolId);
            });
        });
        
        document.querySelectorAll('.delete-tool').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const toolId = button.dataset.id;
                if (confirm('Are you sure you want to delete this tool?')) {
                    await deleteTool(toolId);
                }
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
        
        Utils.showLoading('tool-details-container');
        
        const tool = await API.get(`/tools/${toolId}`);
        
        // Debug log
        console.log('Received tool data:', JSON.stringify(tool, null, 2));
        
        // Determine status display
        let statusBadge = '';
        if (tool.on_status === 'online') {
            statusBadge = '<span class="badge bg-success">Online</span>';
        } else if (tool.on_status === 'Predefined') {
            statusBadge = '<span class="badge bg-info">Clone to Use Predefined Tools</span>';
        } else if (tool.on_status === 'Offline') {
            statusBadge = '<span class="badge bg-warning">Turned Off</span>';
        } else {
            statusBadge = '<span class="badge bg-danger">Inactive</span>';
        }
        
        let detailsHtml = `
            <h4>${tool.name}</h4>
            <p>${tool.description || 'No description'}</p>
            <p><strong>Tool ID:</strong> ${tool.tool_id}</p>
            <p><strong>User ID:</strong> ${tool.user_id}</p>
            <p><strong>Company ID:</strong>${tool.company_id ? tool.company_id : 'Personal Tool'}</p>
            <p><strong>Status:</strong> ${statusBadge} <code class="text-muted">(${tool.on_status})</code></p>
            
            <h5 class="mt-4">Versions</h5>
        `;
        
        if (tool.versions && tool.versions.length > 0) {
            detailsHtml += '<div class="accordion" id="versionsAccordion">';
            
            tool.versions.forEach((version, index) => {
                const releasedData = version.released || {};
                const accordionId = `version-${index}`;
                
                detailsHtml += `
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button ${index > 0 ? 'collapsed' : ''}" type="button" data-bs-toggle="collapse" data-bs-target="#${accordionId}" aria-expanded="${index === 0}" aria-controls="${accordionId}">
                                Version ${version.version} (Port: ${releasedData.port || 'N/A'})
                            </button>
                        </h2>
                        <div id="${accordionId}" class="accordion-collapse collapse ${index === 0 ? 'show' : ''}" data-bs-parent="#versionsAccordion">
                            <div class="accordion-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>Details</h6>
                                        <ul class="list-group mb-3">
                                            <li class="list-group-item"><strong>Method:</strong> ${releasedData.method || 'N/A'}</li>
                                            <li class="list-group-item"><strong>Port:</strong> ${releasedData.port || 'N/A'}</li>
                                            <li class="list-group-item"><strong>Args:</strong> ${releasedData.args || 'N/A'}</li>
                                        </ul>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>Required Environment Variables</h6>
                                        <ul class="list-group mb-3">
`;
                
                // Add required env variables
                if (releasedData.required_env && releasedData.required_env.length > 0) {
                    releasedData.required_env.forEach(env => {
                        detailsHtml += `<li class="list-group-item">${env}</li>`;
                    });
                } else {
                    detailsHtml += `<li class="list-group-item">No required environment variables</li>`;
                }
                
                detailsHtml += `
                                        </ul>
                                    </div>
                                </div>
                                
                                <h6>Environment Variables</h6>
                                <pre class="bg-light p-3 rounded">${JSON.stringify(releasedData.env || {}, null, 2)}</pre>
                                
                                <h6>Full Configuration</h6>
                                <pre class="bg-light p-3 rounded">${JSON.stringify(releasedData, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            detailsHtml += '</div>'; // End accordion
        } else {
            detailsHtml += '<p>No versions available</p>';
        }
        
        // Add JSON representation
        detailsHtml += `
            <h5 class="mt-4">JSON Representation</h5>
            <div class="json-display">
                ${JSON.stringify(tool, null, 2)}
            </div>
        `;
        
        Utils.hideLoading('tool-details-container', detailsHtml);
        
    } catch (error) {
        Utils.hideLoading('tool-details-container', `<p class="text-center text-danger">Error loading tool details: ${error.detail || error.message || 'Unknown error'}</p>`);
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

function resetToolForm() {
    document.getElementById('tool-form').reset();
    document.getElementById('tool-id').value = '';
    document.getElementById('tool-modal-label').textContent = 'Create Tool';
    document.getElementById('tool-avatar-preview').style.display = 'none';
    document.getElementById('avatar-preview').style.display = 'none';
    document.getElementById('tool-name').value = '';
    document.getElementById('tool-description').value = '';
    // Reset version fields
    const versionsContainer = document.getElementById('versions-container');
    while (versionsContainer.firstChild) {
        versionsContainer.removeChild(versionsContainer.firstChild);
    }
    addVersionField();
    
    // Reset file input
    const avatarInput = document.getElementById('tool-avatar');
    if (avatarInput) {
        avatarInput.value = '';
    }
    
    // Add default version
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
    versionDiv.className = 'card mb-3 version-row';
    versionDiv.innerHTML = `
        <div class="card-header d-flex justify-content-between align-items-center">
            <h6 class="mb-0">Version</h6>
            <button type="button" class="btn btn-sm btn-outline-danger remove-version">Remove</button>
        </div>
        <div class="card-body">
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Version Number</label>
                    <input type="text" class="form-control version-number" placeholder="Version (e.g., 1.0.0)" value="${version.version || '1.0.0'}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Method</label>
                    <input type="text" class="form-control version-method" value="sse" readonly>
                    <small class="form-text text-muted">Currently only SSE is supported</small>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Args</label>
                    <input type="text" class="form-control version-args" placeholder="Command arguments" value="${releasedData.args || ''}">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Port</label>
                    <input type="text" class="form-control version-port" placeholder="Port number" value="${releasedData.port || 'The port number will be assigned automatically.'}" disabled>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Environment Variables (JSON)</label>
                    <textarea class="form-control version-env" rows="4" placeholder='{"API_KEY": "your-api-key"}'>${envJson}</textarea>
                    <small class="form-text text-muted">Enter as JSON object</small>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Required Environment Variables (JSON)</label>
                    <textarea class="form-control version-required-env" rows="4" placeholder='["API_KEY"]'>${requiredEnvJson}</textarea>
                    <small class="form-text text-muted">Enter as JSON array</small>
                </div>
            </div>
        </div>
    `;
    
    versionsContainer.appendChild(versionDiv);
    
    // Add event listener to remove button
    versionDiv.querySelector('.remove-version').addEventListener('click', function() {
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
        const onStatus = isActive ? "online" : "Offline";
        
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
            on_status: onStatus,
            avatar_url: '' // Initialize with empty string, will be updated after upload
        };
        
        // First, save the tool to get an ID if it's a new tool
        let response;
        let endpoint = '/tools';
        let newToolId = null;
        
        try {
            if (isUpdate) {
                // Update existing tool
                response = await API.put(`/tools/${toolId}`, toolData);
                console.log('Tool update response:', response);
                Utils.showNotification('Tool updated successfully');
                newToolId = toolId;
            } else {
                // Create new tool
                response = await API.post(endpoint, toolData);
                console.log('Tool creation response:', response);
                Utils.showNotification('Tool created successfully');
                
                // Set the tool ID for the new tool
                if (response.tool_id || response.id) {
                    newToolId = String(response.tool_id || response.id);
                }
            }
        } catch (error) {
            console.error('Error saving tool:', error);
            Utils.showNotification(`Error saving tool: ${error.message}`, 'danger');
            return;
        }
        
        // Handle avatar upload if a file was selected
        const avatarFile = document.getElementById('tool-avatar').files[0];
        if (avatarFile && newToolId) {
            try {
                console.log('Preparing to upload avatar for tool:', newToolId);
                
                // Validate file before upload
                const ALLOWED_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'svg']);
                const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
                
                // Get file extension
                const fileExtension = avatarFile.name.toLowerCase().split('.').pop();
                
                // Check file extension
                if (!ALLOWED_EXTENSIONS.has(fileExtension)) {
                    throw new Error(`Invalid file extension. Allowed extensions: ${Array.from(ALLOWED_EXTENSIONS).join(', ')}`);
                }
                
                // Check file size
                if (avatarFile.size > MAX_FILE_SIZE) {
                    throw new Error(`File too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`);
                }
                
                // Create FormData to send the file
                const formData = new FormData();
                
                // Set proper content type based on file extension
                const contentTypes = {
                    'png': 'image/png',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif',
                    'svg': 'image/svg+xml'
                };
                
                // Create a new File object with proper content type
                const fileWithContentType = new File([avatarFile], avatarFile.name, {
                    type: contentTypes[fileExtension],
                    lastModified: avatarFile.lastModified
                });
                
                // Add the file with the correct parameter name and content type
                formData.append('file', fileWithContentType, avatarFile.name);
                formData.append('is_public', 'true');
                
                // Custom function to handle file uploads
                async function uploadFile(endpoint, formData) {
                    try {
                        const response = await fetch(`${API.getBaseUrl()}${endpoint}`, {
                            method: 'POST',
                            headers: API.getHeaders(false), // Don't set Content-Type for FormData
                            body: formData
                        });
                        
                        if (!response.ok) {
                            const errorData = await response.json().catch(() => ({
                                detail: `HTTP error! Status: ${response.status}`
                            }));
                            throw errorData;
                        }
                        
                        return await response.json();
                    } catch (error) {
                        console.error('File upload error:', error);
                        throw error;
                    }
                }
                
                // Upload the avatar using our custom function
                const uploadResponse = await uploadFile(
                    `/api/avatars/upload/tool/${newToolId}`, 
                    formData
                );
                
                console.log('Avatar upload response:', uploadResponse);
                
                if (!uploadResponse || !uploadResponse.url) {
                    throw new Error('Invalid response from avatar upload');
                }
                
                // Update the tool with the new avatar URL
                const updateResponse = await API.put(`/tools/${newToolId}`, { 
                    ...toolData,
                    avatar_url: uploadResponse.url
                });
                
                console.log('Tool updated with avatar:', updateResponse);
                
            } catch (error) {
                console.error('Avatar upload error:', error);
                if (error.response && error.response.data && error.response.data.detail) {
                    // Handle validation errors
                    const validationError = error.response.data.detail;
                    console.error('Validation error details:', validationError);
                    Utils.showNotification(`Avatar upload failed: ${validationError.error} - ${validationError.details}`, 'danger');
                } else {
                    Utils.showNotification(`Avatar upload failed: ${error.message}`, 'danger');
                }
            }
        }
        
        // Load tools again to refresh the list
        await loadTools();
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('tool-modal'));
        if (modal) {
            modal.hide();
        }
        
        return response;
    } catch (error) {
        console.error('Error saving tool:', error);
        Utils.showNotification(`Error saving tool: ${error.message}`, 'danger');
    }
}

// ... rest of the code remains the same ...
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
        
        let html = '<div class="row">';
        
        tools.forEach(tool => {
            // Check if tool belongs to the Predefined company
            const isPredefined = tool.company_id === "95901eaa-c08d-4b0a-a5d6-3063a622cb98";
            
            // Determine badge style and text based on status
            let badgeClass = "bg-danger";
            let badgeText = "Inactive";
            
            if (tool.on_status === 'online') {
                badgeClass = "bg-success";
                badgeText = "Online";
            } else if (tool.on_status === 'Predefined') {
                badgeClass = "bg-info";
                badgeText = "Clone to Use Predefined Tools";
            } else if (tool.on_status === 'Offline') {
                badgeClass = "bg-warning";
                badgeText = "Turned Off";
            }
            
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card tool-card h-100 ${isPredefined ? '' : ''}" style="${isPredefined ? 'background-color: #d0d4d9;' : ''}" data-id="${tool.tool_id}">
                        <div class="card-body">
                            <h5 class="card-title">${tool.name}</h5>
                            <p class="card-text">${tool.description || 'No description'}</p>
                            <p class="mb-1">
                                <small class="text-muted">Status: 
                                    <span class="badge ${badgeClass}">
                                        ${badgeText}
                                    </span>
                                    <br>
                                    <code class="text-muted">(${tool.on_status})</code>
                                </small>
                            </p>
                            <p class="mb-1"><small class="text-muted">Company: ${tool.company_id ? 'Company Tool' : 'Personal Tool'}</small></p>
                            <p class="mb-0"><small class="text-muted">Versions: ${formatVersions(tool.versions)}</small></p>
                        </div>
                        ${isPredefined ? '<div class="px-3 pb-2 pt-0"><small class="text-dark">Predefined</small></div>' : ''}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        Utils.hideLoading('clone-tools-container', html);
        
        // Add click event listeners to tool cards
        document.querySelectorAll('#clone-tools-container .tool-card').forEach(card => {
            card.addEventListener('click', function() {
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