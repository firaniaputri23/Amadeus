/**
 * Agent Creator JavaScript
 * Handles single-input agent creation with field extraction
 */

// Global state management
let isProcessing = false;
let extractedAgentData = {};
let multiAgentData = null;
let isMultiAgentMode = false;
let isToolsAutofilling = false; // Add flag to track autofill status

// Agent Creator namespace using Module Pattern
const AgentCreator = (function () {
    // Private state
    let availableFields = [];

    // API Module
    const ApiService = {
        getAgentCreatorUrl() {
            const baseUrl = API.getBaseUrl();
            // If running on localhost:8000, assume agent creator is on 8080
            if (baseUrl.includes(':8000')) {
                return baseUrl.replace(':8000', ':8080');
            }
            return baseUrl;
        },

        async makeRequest(endpoint, method = 'GET', body = null) {
            try {
                const options = {
                    method,
                    headers: API.getHeaders(!!body)
                };

                if (body) {
                    options.body = JSON.stringify(body);
                }

                console.log(`Making API request to ${this.getAgentCreatorUrl()}${endpoint}`, { method, options });

                const response = await fetch(`${this.getAgentCreatorUrl()}${endpoint}`, options);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({
                        detail: `HTTP error! Status: ${response.status}`
                    }));
                    throw errorData;
                }

                const responseData = await response.json();
                console.log(`API response from ${endpoint}:`, responseData);
                return responseData;
            } catch (error) {
                console.error(`API error (${method} ${endpoint}):`, error);
                throw error;
            }
        },

        getParseStreamUrl() {
            // Build base URL using the Agent Creator URL, not the main API URL
            const baseUrl = this.getAgentCreatorUrl();
            const streamEndpoint = `/user-input/parse-stream`;
            return `${baseUrl}${streamEndpoint}`;
        },

        getMultiAgentParseUrl() {
            return `${this.getAgentCreatorUrl()}/user-input/parse-multi-agent`;
        },

        async getFieldMetadata() {
            try {
                // First try to get all metadata in a single API call (most efficient)
                try {
                    const metadata = await this.makeRequest('/user-input/field-metadata');
                    console.log('Fetched field metadata in a single call');
                    return metadata;
                } catch (e) {
                    // If that fails (likely 404), fetch data via separate endpoints
                    console.log('Single endpoint not available. ');

                }
            } catch (error) {
                console.error('Error fetching field metadata:', error);
                // Return empty data as fallback
                return {
                    fields: [],
                    descriptions: {}
                };
            }
        },

        async getAvailableTools() {
            try {
                console.log('Fetching available tools from API...');

                // Get company filter value if it exists
                const companyFilter = document.getElementById('company-filter');
                const companyId = companyFilter ? companyFilter.value : null;

                // Build endpoint with company filter if present
                let endpoint = '/tools';
                if (companyId) {
                    endpoint += `?company_id=${companyId}`;
                }

                console.log('API URL:', this.getAgentCreatorUrl() + endpoint);

                // Add a timeout to the fetch operation
                const timeoutId = setTimeout(() => {
                    console.warn('Tool fetch operation is taking longer than expected');
                }, 5000);

                const tools = await API.get(endpoint);
                clearTimeout(timeoutId);

                if (!tools || tools.length === 0) {
                    console.log('No tools found');
                    window.availableTools = [];
                    window.availableToolsMap = {};
                    return [];
                }

                // Store tools globally for UI access
                window.availableTools = tools;

                // Create a map of tool ID to tool object for quick lookup
                window.availableToolsMap = {};
                tools.forEach(tool => {
                    window.availableToolsMap[tool.tool_id] = tool;
                });

                console.log(`Successfully retrieved ${tools.length} tools`);
                console.log('Tool data sample:', tools[0]);
                return tools;
            } catch (error) {
                console.error('Error fetching available tools:', error);

                // Try to get more detailed error information
                let errorDetails = '';
                if (error.status) errorDetails += ` Status: ${error.status}.`;
                if (error.detail) errorDetails += ` Detail: ${error.detail}.`;
                if (error.message) errorDetails += ` Message: ${error.message}.`;

                console.error('Error details:', errorDetails || 'No additional details');

                // Show more detailed error information
                const errorMessage = error.detail || error.message || JSON.stringify(error);
                Utils.showNotification(`Error loading available tools: ${errorMessage}`, 'warning');

                // Initialize empty tools arrays
                window.availableTools = [];
                window.availableToolsMap = {};
                return [];
            }
        },


        async autofillField(field, jsonField, existingValue = '', availableTools = []) {
            //hanya untuk tools sepertinya
            console.log('Method called: ApiService.autofillField', { field });
            try {
                const requestBody = {
                    field_name: field,
                    json_field: jsonField,
                    existing_field_value: existingValue,
                    available_tools: []  // Always send empty tools array, backend will get all tools
                };

                // We'll let the backend handle fetching all tools
                if (field === 'tools') {
                    requestBody.return_tool_ids = true;
                }

                console.log(`Sending autofill request for ${field}:`, requestBody);

                const responseData = await this.makeRequest('/agent-creator-autofill/invoke', 'POST', requestBody);
                console.log(`Autofill response for ${field}:`, responseData);

                return responseData;
            } catch (error) {
                console.error(`Error in autofillField for ${field}:`, error);
                // Return empty result on error
                return {
                    field_name: field,
                    autofilled_value: field === 'tools' ? [] : '',
                    reasoning: `Autofill failed: ${error.message}`
                };
            }
        }
    };

    // UI Module
    const UiManager = {
        // Add formatVersions helper function
        formatVersions(versions) {
            if (!versions || versions.length === 0) {
                return 'None';
            }

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
        },

        // Chat UI management
        addMessage(message, isBot = false) {
            const chatContainer = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isBot ? 'bot' : 'user'}`;

            const avatarHtml = isBot
                ? '<div class="avatar"><i class="bi bi-robot"></i></div>'
                : '<div class="avatar"><i class="bi bi-person-circle fs-4"></i></div>';

            messageDiv.innerHTML = `
                ${avatarHtml}
                <div class="message-bubble">${message}</div>
            `;

            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        },

        addUserMessage(message) {
            this.addMessage(message, false);
        },

        addBotMessage(message) {
            this.addMessage(message, true);
        },

        addBotTypingIndicator() {
            const chatContainer = document.getElementById('chat-container');
            const indicatorDiv = document.createElement('div');
            indicatorDiv.className = 'message bot';
            indicatorDiv.id = 'typing-indicator';
            indicatorDiv.innerHTML = `
                <div class="avatar"><i class="bi bi-robot"></i></div>
                <div class="message-bubble">
                    <div class="typing">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            `;
            chatContainer.appendChild(indicatorDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        },

        removeTypingIndicator() {
            const indicator = document.getElementById('typing-indicator');
            if (indicator) {
                indicator.remove();
            }
        },

        clearChat() {
            document.getElementById('chat-container').innerHTML = '';
        },

        // Field help modal
        showFieldHelpModal() {
            console.log('Method called: UiManager.showFieldHelpModal');
            const modal = new bootstrap.Modal(document.getElementById('field-help-modal'));
            modal.show();
        },

        updateFieldDescriptions(fields) {
            const fieldDescriptionsContainer = document.getElementById('field-descriptions');

            if (!fields || fields.length === 0) {
                fieldDescriptionsContainer.innerHTML = '<p>No field descriptions available</p>';
                return;
            }

            const fieldItems = fields.map(field => `
                <div class="list-group-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${field.name}</h5>
                    </div>
                    <p class="mb-1">${field.description}</p>
                </div>
            `);

            fieldDescriptionsContainer.innerHTML = fieldItems.join('');
        },

        // Agent preview formatting
        formatFieldValue(field, value) {
            if (field === 'tools') {
                if (Array.isArray(value) && value.length > 0) {
                    const toolBadges = value.map(toolId => {
                        let toolName = toolId;
                        if (window.availableToolsMap && window.availableToolsMap[toolId]) {
                            toolName = window.availableToolsMap[toolId].name || toolId;
                        }
                        return `<span class="badge bg-dark border border-secondary text-yellow me-1 mb-1">${toolName}</span>`;
                    });
                    return toolBadges.join(' ');
                }
                return '<span class="text-secondary opacity-25 italic">No modules linked</span>';
            }

            if (field === 'keywords') {
                if (Array.isArray(value) && value.length > 0) {
                    return value.map(keyword =>
                        `<span class="badge bg-glass border border-secondary text-cyan me-1 mb-1">${keyword}</span>`
                    ).join(' ');
                }
                return '<span class="text-secondary opacity-25 italic">No keywords established</span>';
            }

            if (value === undefined || value === null || value === '') {
                return '<span class="text-secondary opacity-25 italic">Not yet defined...</span>';
            }

            if (field === 'on_status') {
                return value ? '<span class="text-cyan fw-bold">ACTIVE</span>' : '<span class="text-secondary opacity-50 fw-bold">IDLE</span>';
            }

            return `<span class="text-white">${value}</span>`;
        },

        updateAgentPreview(agentData, isMultiAgent = false) {
            const previewContainer = document.getElementById('agent-preview');

            if (!agentData || (Object.keys(agentData).length === 0 && !isMultiAgent)) {
                previewContainer.innerHTML = `
                    <div class="text-center py-5 opacity-50">
                        <i class="bi bi-magic display-3 d-block mb-3 text-yellow"></i>
                        <p class="small text-secondary text-uppercase" style="letter-spacing: 2px;">Awaiting Extraction</p>
                    </div>
                `;
                return;
            }

            // If it's multi-agent mode and we have variations
            if (isMultiAgent && multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                const variations = multiAgentData.agent_variations;

                let previewHtml = `
                    <div class="mb-4">
                        <h6 class="text-yellow text-uppercase small mb-3 fw-bold" style="letter-spacing: 1px;">Core Swarm Matrix</h6>
                `;

                // Display common attributes
                for (const [field, value] of Object.entries(multiAgentData.common_attributes)) {
                    if (value && typeof value !== 'object' && field !== 'keywords') {
                        const formattedValue = this.formatFieldValue(field, value);
                        previewHtml += `
                            <div class="field-card filled mb-2">
                                <label class="field-label">${field}</label>
                                <p class="field-value">${formattedValue}</p>
                            </div>
                        `;
                    }
                }

                // Add keywords
                const keywords = multiAgentData.common_attributes.keywords || extractedAgentData.keywords;
                if (keywords && Array.isArray(keywords) && keywords.length > 0) {
                    previewHtml += `
                        <div class="field-card filled mb-2">
                            <label class="field-label">Swarm Keywords</label>
                            <div class="mt-1">${this.formatFieldValue('keywords', keywords)}</div>
                        </div>
                    `;
                }

                previewHtml += `</div><h6 class="text-yellow text-uppercase small mb-3 fw-bold" style="letter-spacing: 1px;">Agent Nodes (${variations.length})</h6>`;

                // Display each agent variation
                variations.forEach((agent, index) => {
                    previewHtml += `
                        <div class="tool-preview-card mb-3">
                            <div class="tool-preview-header">
                                <span class="text-white fw-bold"><i class="bi bi-robot me-2"></i>Node ${index + 1}: ${agent.agent_name || 'Unnamed'}</span>
                            </div>
                            <div class="p-3">
                    `;

                    const completeAgent = { ...multiAgentData.common_attributes, ...agent };

                    for (const [field, value] of Object.entries(completeAgent)) {
                        if (value && typeof value !== 'object' && field !== 'keywords' && field !== 'agent_name') {
                            const formattedValue = this.formatFieldValue(field, value);
                            const isAgentSpecific = !multiAgentData.common_attributes.hasOwnProperty(field) ||
                                multiAgentData.common_attributes[field] !== value;

                            previewHtml += `
                                <div class="mb-2 p-2 rounded" style="background: ${isAgentSpecific ? 'rgba(0, 255, 255, 0.03)' : 'transparent'}">
                                    <label class="field-label mb-0" style="color: ${isAgentSpecific ? 'var(--q-cyan)' : 'var(--q-yellow)'}; font-size: 0.65rem;">${field}</label>
                                    <p class="field-value mb-0">${formattedValue}</p>
                                </div>
                            `;
                        }
                    }

                    // Add agent-specific tool selection
                    previewHtml += `
                        <div class="mt-3">
                            <label class="field-label">Module Integration</label>
                            <div class="d-flex gap-2 mb-2">
                                <button type="button" class="btn btn-xs btn-outline-quantum select-all-agent-tools" data-agent-index="${index}">Link All</button>
                                <button type="button" class="btn btn-xs btn-outline-secondary deselect-all-agent-tools" data-agent-index="${index}">Unlink All</button>
                            </div>
                            
                            <div class="tool-selection-container p-2 bg-dark rounded border border-secondary" id="agent-${index}-tool-checkboxes-container" style="max-height: 200px; overflow-y: auto;">
                                <div class="loading-indicator">
                                    <div class="spinner-border spinner-border-sm text-yellow" role="status"></div>
                                    <span class="ms-2 small text-secondary">Awaiting modules...</span>
                                </div>
                            </div>
                        </div>
                    `;

                    previewHtml += `</div></div>`;
                });

                previewContainer.innerHTML = previewHtml;

                variations.forEach((agent, index) => {
                    this.populateAgentToolCheckboxes(index, agent.tools || []);
                });

                this.setupAgentToolInteractionListeners();

            } else {
                // Standard single agent preview
                let previewHtml = '';

                // Agent Header Card
                previewHtml += `
                    <div class="field-card filled mb-4">
                        <div class="d-flex align-items-center gap-3">
                            <div class="avatar bg-yellow text-dark rounded-circle" style="width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                                <i class="bi bi-robot"></i>
                            </div>
                            <div class="overflow-hidden">
                                <label class="field-label mb-0" style="font-size: 0.6rem;">Agent Identity</label>
                                <h5 class="text-white mb-0 text-truncate">${agentData.agent_name || 'Designating...'}</h5>
                            </div>
                        </div>
                    </div>
                `;

                const fields = [
                    { key: 'agent_id', label: 'Network ID', icon: 'bi-hash' },
                    { key: 'description', label: 'Primary Directive', icon: 'bi-card-text' },
                    { key: 'agent_style', label: 'Persona Profile', icon: 'bi-palette' },
                    { key: 'company_id', label: 'Corporate Entity', icon: 'bi-building' }
                ];

                fields.forEach(field => {
                    const value = agentData[field.key];
                    const isFilled = value && value !== '';
                    previewHtml += `
                        <div class="field-card ${isFilled ? 'filled' : ''}">
                            <label class="field-label">
                                <i class="bi ${field.icon} me-1"></i> ${field.label}
                            </label>
                            <p class="field-value">${this.formatFieldValue(field.key, value)}</p>
                        </div>
                    `;
                });

                // Add keywords
                if (agentData.keywords && Array.isArray(agentData.keywords) && agentData.keywords.length > 0) {
                    previewHtml += `
                        <div class="field-card filled">
                            <label class="field-label">Core Keywords</label>
                            <div class="mt-1">${this.formatFieldValue('keywords', agentData.keywords)}</div>
                        </div>
                    `;
                }

                // Add tools selection
                previewHtml += `
                    <div class="mt-4">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                             <h6 class="text-yellow text-uppercase small fw-bold m-0" style="letter-spacing: 1px;">Module Ecosystem</h6>
                             <div class="d-flex gap-1">
                                <button type="button" class="btn btn-xs btn-outline-quantum" id="select-all-tools">Link All</button>
                                <button type="button" class="btn btn-xs btn-outline-secondary" id="deselect-all-tools">Unlink All</button>
                             </div>
                        </div>
                        
                        <div class="mb-3">
                            <div class="input-wrapper py-1 px-3" style="border-radius: 8px;">
                                <i class="bi bi-search text-secondary small"></i>
                                <input type="text" class="form-control form-control-sm border-0 bg-transparent" id="tool-search" placeholder="Filter modules...">
                            </div>
                        </div>
                        
                        <div class="tool-selection-container p-3 bg-dark bg-opacity-50 rounded border border-secondary" id="tool-checkboxes-container" style="max-height: 300px; overflow-y: auto;">
                            <!-- Tool checkboxes will be added here dynamically -->
                            ${!window.availableTools || window.availableTools.length === 0 ?
                        `<div class="loading-indicator">
                                    <div class="spinner-border spinner-border-sm text-yellow" role="status"></div>
                                    <span class="ms-2 small text-secondary">Synchronizing tool library...</span>
                                </div>` : ''
                    }
                        </div>
                    </div>
                `;

                previewContainer.innerHTML = previewHtml;

                this.setupToolInteractionListeners();
            }
        },

        setupToolInteractionListeners() {
            // Populate tool checkboxes first
            this.populateToolCheckboxes();

            // Tool checkboxes change listener
            this.setupToolCheckboxListeners();

            // Select/deselect all buttons
            const selectAllBtn = document.getElementById('select-all-tools');
            const deselectAllBtn = document.getElementById('deselect-all-tools');

            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => {
                    const checkboxes = document.querySelectorAll('.tool-checkbox');
                    checkboxes.forEach(checkbox => {
                        // Only update visible checkboxes if search is active
                        const checkboxItem = checkbox.closest('.tool-checkbox-item');
                        if (checkboxItem && checkboxItem.style.display !== 'none') {
                            checkbox.checked = true;
                            // Trigger change event
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                });
            }

            if (deselectAllBtn) {
                deselectAllBtn.addEventListener('click', () => {
                    const checkboxes = document.querySelectorAll('.tool-checkbox');
                    checkboxes.forEach(checkbox => {
                        // Only update visible checkboxes if search is active
                        const checkboxItem = checkbox.closest('.tool-checkbox-item');
                        if (checkboxItem && checkboxItem.style.display !== 'none') {
                            checkbox.checked = false;
                            // Trigger change event
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                });
            }

            // Search functionality
            const searchInput = document.getElementById('tool-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const searchTerm = e.target.value.toLowerCase().trim();
                    const toolItems = document.querySelectorAll('.tool-checkbox-item');

                    toolItems.forEach(item => {
                        const toolName = item.getAttribute('data-tool-name');
                        if (toolName.includes(searchTerm)) {
                            item.style.display = '';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            }
        },

        populateToolCheckboxes() {
            const container = document.getElementById('tool-checkboxes-container');
            if (!container) return;

            if (!window.availableTools || window.availableTools.length === 0) {
                container.innerHTML = `
                    <div class="p-3 text-center opacity-50 small">
                        <i class="bi bi-exclamation-triangle-fill text-yellow d-block mb-2 fs-4"></i>
                        NO MODULES DETECTED
                    </div>
                `;
                return;
            }

            // Show loading indicator if we're autofilling
            if (isToolsAutofilling) {
                container.innerHTML = `
                    <div class="loading-indicator d-flex align-items-center justify-content-center p-5">
                        <div class="spinner-border spinner-border-sm" style="color: var(--q-yellow);" role="status">
                            <span class="visually-hidden">Loading tools...</span>
                        </div>
                        <span class="ms-3 text-secondary small text-uppercase fw-bold" style="letter-spacing: 1px;">Synthesizing module dependencies...</span>
                    </div>
                `;
                return;
            }

            // Convert current tool array to a set for faster lookup
            const selectedToolsSet = new Set(
                Array.isArray(extractedAgentData.tools) ? extractedAgentData.tools : []
            );

            // Create a copy of available tools for sorting
            const sortedTools = [...window.availableTools];

            // Sort tools - checked tools first
            sortedTools.sort((a, b) => {
                const aIsChecked = selectedToolsSet.has(a.tool_id);
                const bIsChecked = selectedToolsSet.has(b.tool_id);

                if (aIsChecked && !bIsChecked) return -1;
                if (!aIsChecked && bIsChecked) return 1;
                return 0;
            });

            // Add tools as checkboxes
            let checkboxesHtml = '<div class="tool-checkboxes">';

            sortedTools.forEach(tool => {
                // Check if this tool is in the selected tools set
                const isChecked = selectedToolsSet.has(tool.tool_id);
                const statusColor = tool.on_status === 'Online' ? 'var(--q-yellow)' : 'rgba(255,255,255,0.2)';

                checkboxesHtml += `
            <div class="form-check mb-2 tool-checkbox-item" data-tool-name="${tool.name.toLowerCase()}" data-tool-id="${tool.tool_id}">
                <div class="d-flex align-items-start p-3 border rounded tool-card-select ${isChecked ? 'selected' : ''}" 
                     style="background: rgba(255,255,255,0.02); border-color: ${isChecked ? 'var(--q-yellow)' : 'var(--border-color)'} !important; border-width: 1px; transition: all 0.3s; ${isChecked ? 'box-shadow: 0 0 15px rgba(255, 255, 0, 0.05);' : ''}">
                    <div class="me-3 mt-1">
                        <input class="form-check-input tool-checkbox" 
                               type="checkbox" 
                               value="${tool.tool_id}" 
                               id="tool-${tool.tool_id}"
                               style="width: 18px; height: 18px; border-color: var(--q-yellow); background-color: transparent;"
                               ${isChecked ? 'checked' : ''}>
                    </div>
                    <div class="flex-grow-1 overflow-hidden">
                        <label class="form-check-label d-block text-white fw-bold mb-1 text-truncate" for="tool-${tool.tool_id}" style="font-size: 0.9rem; letter-spacing: 0.5px;">
                            ${tool.name}
                        </label>
                        <div class="small text-secondary mb-2 text-truncate" style="opacity: 0.7; font-size: 0.75rem;">
                            ${tool.description || 'No data segment available'}
                        </div>
                        <div class="d-flex align-items-center">
                            <div style="width: 6px; height: 6px; border-radius: 50%; background: ${statusColor}; box-shadow: 0 0 5px ${statusColor}; margin-right: 8px;"></div>
                            <span class="text-secondary" style="font-size: 0.65rem; letter-spacing: 1px; text-transform: uppercase;">
                                ${tool.on_status === 'Online' ? 'Active Matrix' : 'Offline'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
            });

            checkboxesHtml += '</div>';
            container.innerHTML = checkboxesHtml;
        },

        setupToolCheckboxListeners() {
            const checkboxes = document.querySelectorAll('.tool-checkbox');

            checkboxes.forEach(checkbox => {
                checkbox.addEventListener('change', () => {
                    // Get all selected tools
                    const selectedTools = Array.from(
                        document.querySelectorAll('.tool-checkbox:checked')
                    ).map(cb => cb.value);

                    console.log('Tool selection changed:', selectedTools);

                    // Update the tools in extracted agent data
                    extractedAgentData.tools = selectedTools;

                    // Check if we have the required fields to enable the create button
                    const hasRequiredFields = DataProcessor.hasRequiredFields(extractedAgentData);
                    UiManager.updateCreateButtonState(hasRequiredFields);

                    // Re-populate the tools to ensure checked ones are at the top
                    this.populateToolCheckboxes();
                });
            });
        },

        // Form UI controls
        updateCreateButtonState(enabled) {
            document.getElementById('create-agent').disabled = !enabled;
        },

        getModelSettings() {
            // Use default values since the model options section was removed
            const model = window.defaultParserModel || "custom-vlm";
            const temperature = window.defaultTemperature !== undefined ? window.defaultTemperature : 0;
            const isMultiAgent = document.getElementById('multi-agent-toggle').checked;
            return { model, temperature, isMultiAgent };
        },

        getUserInput() {
            return document.getElementById('user-input').value.trim();
        },

        clearUserInput() {
            document.getElementById('user-input').value = '';
        },

        populateAgentToolCheckboxes(agentIndex, selectedTools = []) {
            // Cache DOM container lookup
            const containerId = `agent-${agentIndex}-tool-checkboxes-container`;
            const container = document.getElementById(containerId);
            if (!container) return;

            // Early return conditions with template literals stored as constants
            const NO_TOOLS_TEMPLATE = `
        <div class="alert bg-dark border border-secondary text-info d-flex align-items-center mb-3">
            <i class="bi bi-info-circle me-2"></i>
            <div>No available tools found. Please wait for tools to load or check your connection.</div>
        </div>
    `;

            const LOADING_TEMPLATE = `
                <div class="loading-indicator">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading tools...</span>
                    </div>
                    <span class="ms-2">Auto-selecting relevant tools...</span>
                </div>
            `;

            if (!window.availableTools?.length) {
                container.innerHTML = NO_TOOLS_TEMPLATE;
                return;
            }

            if (isToolsAutofilling) {
                container.innerHTML = LOADING_TEMPLATE;
                return;
            }

            // Create a Map for O(1) lookup of selected tools
            const selectedToolsMap = new Map(
                Array.isArray(selectedTools) ?
                    selectedTools.map(id => [id, true]) :
                    []
            );

            // Create a copy of available tools for sorting
            const sortedTools = [...window.availableTools];

            // Sort tools - checked tools first
            sortedTools.sort((a, b) => {
                const aIsChecked = selectedToolsMap.has(a.tool_id);
                const bIsChecked = selectedToolsMap.has(b.tool_id);

                if (aIsChecked && !bIsChecked) return -1;
                if (!aIsChecked && bIsChecked) return 1;
                return 0;
            });

            // Use DocumentFragment for better performance
            const fragment = document.createDocumentFragment();
            const toolCheckboxesDiv = document.createElement('div');
            toolCheckboxesDiv.className = 'tool-checkboxes';

            // Create a template function for tool HTML
            const createToolHTML = (tool, isChecked) => {
                const div = document.createElement('div');
                div.className = 'tool-checkbox-item mb-2';
                div.dataset.agentIndex = agentIndex;
                div.dataset.toolName = tool.name.toLowerCase();
                div.dataset.toolId = tool.tool_id;

                const statusColor = tool.on_status === 'Online' ? 'var(--q-yellow)' : 'rgba(255,255,255,0.2)';

                div.innerHTML = `
                    <div class="d-flex align-items-center p-2 rounded" 
                         style="background: rgba(255,255,255,0.03); border: 1px solid ${isChecked ? 'var(--q-yellow)' : 'var(--border-color)'}; transition: all 0.2s;">
                        <input class="form-check-input agent-tool-checkbox me-3 mt-0" 
                               type="checkbox" 
                               value="${tool.tool_id}" 
                               id="agent-${agentIndex}-tool-${tool.tool_id}"
                               data-agent-index="${agentIndex}"
                               style="border-color: var(--q-yellow); background-color: transparent;"
                               ${isChecked ? 'checked' : ''}>
                        <div class="flex-grow-1 overflow-hidden">
                            <label class="form-check-label d-block text-white fw-bold small text-truncate" for="agent-${agentIndex}-tool-${tool.tool_id}" style="font-size: 0.75rem;">
                                ${tool.name}
                            </label>
                            <div class="text-secondary text-truncate" style="font-size: 0.6rem; opacity: 0.8;">
                                ${tool.description || 'No data segment'}
                            </div>
                        </div>
                        <div class="ms-2">
                            <div style="width: 8px; height: 8px; border-radius: 50%; background: ${statusColor}; box-shadow: 0 0 5px ${statusColor};"></div>
                        </div>
                    </div>
                `;
                return div;
            };

            // Batch process tools
            sortedTools.forEach(tool => {
                const isChecked = selectedToolsMap.has(tool.tool_id);
                toolCheckboxesDiv.appendChild(createToolHTML(tool, isChecked));
            });

            fragment.appendChild(toolCheckboxesDiv);
            container.innerHTML = ''; // Clear container once
            container.appendChild(fragment);

            // Setup event listeners efficiently
            this.setupAgentToolCheckboxListeners(agentIndex);
        },

        setupAgentToolCheckboxListeners(agentIndex) {
            // Cache the container to limit DOM traversal
            const container = document.getElementById(`agent-${agentIndex}-tool-checkboxes-container`);
            if (!container) return;

            // Use event delegation instead of multiple listeners
            container.addEventListener('change', (event) => {
                const checkbox = event.target;
                if (!checkbox.classList.contains('agent-tool-checkbox')) return;

                // Batch DOM operations
                const selectedTools = Array.from(
                    container.querySelectorAll('.agent-tool-checkbox:checked')
                ).map(cb => cb.value);

                // Guard clause for multiAgentData
                if (!multiAgentData?.agent_variations?.[agentIndex]) return;

                // Update tools and button state
                multiAgentData.agent_variations[agentIndex].tools = selectedTools;

                // Update create button state only when needed
                const hasMultiAgentData = multiAgentData?.agent_variations?.length > 0;
                UiManager.updateCreateButtonState(hasMultiAgentData);

                // Re-populate to ensure checked tools are at the top
                this.populateAgentToolCheckboxes(agentIndex, selectedTools);
            });
        },

        setupAgentToolInteractionListeners() {
            // Agent-specific tool buttons
            document.querySelectorAll('.select-all-agent-tools').forEach(button => {
                const agentIndex = button.getAttribute('data-agent-index');
                button.addEventListener('click', () => {
                    const checkboxes = document.querySelectorAll(`.agent-tool-checkbox[data-agent-index="${agentIndex}"]`);
                    checkboxes.forEach(checkbox => {
                        // Only update visible checkboxes if search is active
                        const checkboxItem = checkbox.closest('.agent-tool-checkbox-item');
                        if (checkboxItem && checkboxItem.style.display !== 'none') {
                            checkbox.checked = true;
                            // Trigger change event
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                });
            });

            document.querySelectorAll('.deselect-all-agent-tools').forEach(button => {
                const agentIndex = button.getAttribute('data-agent-index');
                button.addEventListener('click', () => {
                    const checkboxes = document.querySelectorAll(`.agent-tool-checkbox[data-agent-index="${agentIndex}"]`);
                    checkboxes.forEach(checkbox => {
                        // Only update visible checkboxes if search is active
                        const checkboxItem = checkbox.closest('.agent-tool-checkbox-item');
                        if (checkboxItem && checkboxItem.style.display !== 'none') {
                            checkbox.checked = false;
                            // Trigger change event
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                });
            });

            // Search functionality for agent-specific tools
            document.querySelectorAll('.agent-tool-search').forEach(searchInput => {
                const agentIndex = searchInput.getAttribute('data-agent-index');
                searchInput.addEventListener('input', (e) => {
                    const searchTerm = e.target.value.toLowerCase().trim();
                    const toolItems = document.querySelectorAll(`.agent-tool-checkbox-item[data-agent-index="${agentIndex}"]`);

                    toolItems.forEach(item => {
                        const toolName = item.getAttribute('data-tool-name');
                        if (toolName.includes(searchTerm)) {
                            item.style.display = '';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            });
        },

        // Update the status indicator for tool autofill
        updateToolAutofillStatus(isAutofilling) {
            document.querySelectorAll('.autofill-status').forEach(statusElement => {
                if (isAutofilling) {
                    statusElement.innerHTML = `<i class="bi bi-arrow-repeat spin"></i> Auto-selecting tools...`;
                    statusElement.classList.add('autofilling');
                    statusElement.classList.remove('complete');
                } else {
                    statusElement.innerHTML = `<i class="bi bi-check-circle-fill text-success"></i> Tools loaded`;
                    statusElement.classList.remove('autofilling');
                    statusElement.classList.add('complete');
                }
            });
        }
    };

    // Data processing module
    const DataProcessor = {
        mergeData(existingData, newData) {
            //POTENSI NOT USED
            console.log('Method called: DataProcessor.mergeData');
            const result = { ...existingData };

            for (const [key, value] of Object.entries(newData)) {
                if (value && value !== "") {
                    if (Array.isArray(value) && Array.isArray(result[key])) {
                        // Combine arrays without duplicates
                        result[key] = [...new Set([...result[key], ...value])];
                    } else {
                        result[key] = value;
                    }
                }
            }

            return result;
        },

        processToolsValue(value) {
            // Handle tools field special case
            if (Array.isArray(value) && value.length > 0) {
                console.log(`Using array of tool IDs directly:`, value);
                return value;
            } else if (typeof value === 'string' && value.trim()) {
                // If it's a string, try to parse it (might be JSON)
                try {
                    const parsedValue = JSON.parse(value);
                    if (Array.isArray(parsedValue)) {
                        console.log(`Parsed string to array of tool IDs:`, parsedValue);
                        return parsedValue;
                    } else if (parsedValue && typeof parsedValue === 'object') {
                        // If it's an object with an array property, try to find it
                        for (const key in parsedValue) {
                            if (Array.isArray(parsedValue[key])) {
                                console.log(`Extracted array from object property ${key}:`, parsedValue[key]);
                                return parsedValue[key];
                            }
                        }
                    }
                } catch (e) {
                    // Parsing failed, but don't fallback to default yet
                    console.log(`JSON parsing failed: ${e.message}`);

                    // If it's a string, but not JSON, it might be a comma-separated list
                    if (value.includes(',')) {
                        const items = value.split(',').map(item => item.trim()).filter(Boolean);
                        if (items.length > 0) {
                            console.log(`Parsed comma-separated list:`, items);
                            return items;
                        }
                    }
                }
            }

            // Return empty array if no valid tools found
            console.log(`No valid tools found, returning empty array`);
            return [];
        },

        updateFieldWithAutofillValue(data, field, value) {
            const result = { ...data };

            if (field === 'tools') {
                console.log(`Processing tools value:`, value);
                result[field] = this.processToolsValue(value);
                console.log(`Final tools value:`, result[field]);
            } else {
                result[field] = value;
            }

            return result;
        },

        hasRequiredFields(data) {
            const requiredFields = ['agent_name', 'description'];
            return requiredFields.every(field => data[field] && data[field] !== '');
        },

        generateResponseFromExtractedData(extractedData) {
            const extractedFields = Object.entries(extractedData)
                .filter(([_, value]) => value && value !== "")
                .map(([field, _]) => field);

            if (extractedFields.length === 0) {
                return "Protocol failed to isolate specific parameters within the neural link. High-level directives required regarding the agent's primary mission and behavioral logic.";
            }

            const hasCoreFunctionality = extractedData.agent_name && extractedData.description;
            let response = "Extraction successful. ";

            if (hasCoreFunctionality) {
                response += `I've successfully mapped the structural blueprints for <strong>${extractedData.agent_name}</strong>. Clusters identified: <code>${extractedFields.join(', ')}</code>. `;
                response += "The architecture is being visualized in the preview panel. Shall we initiate tool integration or refine the system parameters?";
            } else {
                response += `I've captured partial parameters (<code>${extractedFields.join(', ')}</code>), but the blueprint remains structurally unstable. `;
                const missingRequired = [];
                if (!extractedData.agent_name) missingRequired.push("Identification (Name)");
                if (!extractedData.description) missingRequired.push("Directives (Description)");
                response += `Please provide the missing ${missingRequired.join(' and ')} to stabilize the architecture.`;
            }

            return response;
        },

        prepareAgentDataForCreation(data) {
            // Make a deep copy to avoid modifying the original
            const agentData = JSON.parse(JSON.stringify(data));

            // Process tools as array of UUIDs
            if (agentData.tools && Array.isArray(agentData.tools)) {
                // Keep as is, already processed
            } else if (typeof agentData.tools === 'string') {
                agentData.tools = this.processToolsValue(agentData.tools);
            } else {
                agentData.tools = [];
            }

            // Ensure on_status is a boolean
            agentData.on_status = agentData.on_status !== false;

            // Handle company_id - set to null if empty string or not provided
            if (!agentData.company_id || agentData.company_id === '') {
                agentData.company_id = null;
            }

            return agentData;
        },

        prepareMultiAgentDataForCreation(commonData, variations) {
            const agents = [];

            // For each variation, create a complete agent by merging with common data
            variations.forEach(variation => {
                // Start with common data
                const agentData = { ...commonData };

                // Convert agent_style to agent_name for consistency if needed
                if (agentData.agent_style && !agentData.agent_name) {
                    agentData.agent_name = agentData.agent_style;
                    delete agentData.agent_style;
                }

                // Merge variation-specific fields
                for (const [key, value] of Object.entries(variation)) {
                    // Convert agent_style to agent_name for consistency
                    if (key === 'agent_style' && !variation.agent_name) {
                        agentData.agent_name = value;
                    }
                    // For keywords, if we have agent-specific keywords, use those instead of common ones
                    else if (key === 'keywords' && Array.isArray(value) && value.length > 0) {
                        agentData.keywords = value;
                    }
                    // For tools, handle agent-specific tools
                    else if (key === 'tools' && Array.isArray(value)) {
                        agentData.tools = value;
                    }
                    // For all other fields, overwrite the common data with variation-specific data
                    else if (key !== 'agent_style' && value !== undefined && value !== null) {
                        agentData[key] = value;
                    }
                }

                // Ensure agent has a name
                if (!agentData.agent_name) {
                    agentData.agent_name = variation.agent_name || 'Unnamed Agent';
                }

                // Ensure agent has a tools array
                if (!agentData.tools) {
                    agentData.tools = [];
                }

                // Prepare and add the agent
                agents.push(this.prepareAgentDataForCreation(agentData));
            });

            return agents;
        }
    };

    // Main controller
    const Controller = {
        async init() {
            try {
                console.log('Initializing Agent Creator...');

                // Add custom CSS for tool selection
                this.addToolSelectionStyles();

                // Show initial loading state
                UiManager.addBotMessage("Loading agent creator...");

                // Set up event listeners
                this.setupEventListeners();

                // Initialize example boxes visibility based on multi-agent mode
                const isMultiMode = document.getElementById('multi-agent-toggle').checked;
                document.querySelectorAll('.example-box.single-agent').forEach(box => {
                    box.style.display = isMultiMode ? 'none' : 'block';
                });
                document.querySelectorAll('.example-box.multi-agent').forEach(box => {
                    box.style.display = isMultiMode ? 'block' : 'none';
                });

                // Clear the initial loading message
                UiManager.clearChat();

                // Start with initial bot message and loading indicator
                UiManager.addBotMessage("Loading available agent tools...");

                // Load initial data in parallel
                await Promise.all([
                    this.loadAvailableFields(),
                    this.loadAvailableTools()
                ]);

                // Clear chat and add welcome message
                UiManager.clearChat();
                UiManager.addBotMessage("Give me a detailed description of an agent you would like to make.");

                console.log('Agent Creator initialized successfully');
            } catch (error) {
                console.error("Error initializing agent creator:", error);
                UiManager.clearChat();
                UiManager.addBotMessage("There was an error loading the Agent Creator. Please try refreshing the page.");
                Utils.showNotification("Failed to initialize agent creator. Please reload the page.", "danger");
            }
        },

        setupEventListeners() {
            // Send button
            document.getElementById('send-message').addEventListener('click', () => {
                this.handleUserInput();
            });

            // Send on Enter key (but allow shift+enter for new lines)
            document.getElementById('user-input').addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleUserInput();
                }
            });

            // Show field help modal
            document.getElementById('show-field-help').addEventListener('click', () => {
                UiManager.showFieldHelpModal();
            });

            // Create agent button
            document.getElementById('create-agent').addEventListener('click', () => {
                this.createAgent();
            });

            // Reset agent button
            document.getElementById('reset-agent').addEventListener('click', () => {
                this.resetAgentData();
            });

            // Temperature slider and model select were removed - handle this gracefully
            const tempSlider = document.getElementById('temperature');
            const tempValue = document.getElementById('temp-value');

            if (tempSlider && tempValue) {
                tempSlider.addEventListener('input', () => {
                    tempValue.textContent = tempSlider.value;
                });
            }

            // Add event listener for multi-agent toggle
            document.getElementById('multi-agent-toggle').addEventListener('change', (e) => {
                isMultiAgentMode = e.target.checked;

                // Toggle visibility of example buttons based on multi-agent mode
                const singleAgentExamples = document.querySelectorAll('.example-btn.single-agent');
                const multiAgentExamples = document.querySelectorAll('.example-btn.multi-agent');

                singleAgentExamples.forEach(btn => {
                    if (isMultiAgentMode) {
                        btn.classList.add('d-none');
                    } else {
                        btn.classList.remove('d-none');
                    }
                });

                multiAgentExamples.forEach(btn => {
                    if (isMultiAgentMode) {
                        btn.classList.remove('d-none');
                    } else {
                        btn.classList.add('d-none');
                    }
                });

                // Update UI based on toggle state
                if (isMultiAgentMode) {
                    UiManager.addBotMessage("Multi-agent mode enabled. Please describe multiple agents and how they differ from each other.");
                } else {
                    // Only add message if we were previously in multi-agent mode with data
                    if (multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                        UiManager.addBotMessage("Multi-agent mode disabled. Switching to single agent creation mode.");
                        multiAgentData = null;
                        UiManager.updateAgentPreview(extractedAgentData, false);
                    }
                }
            });

            // Add event listeners for example buttons (chips)
            document.querySelectorAll('.example-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    const exampleText = chip.getAttribute('data-example');
                    if (exampleText) {
                        const inputField = document.getElementById('user-input');
                        inputField.value = exampleText;
                        // Focus on the input field
                        inputField.focus();
                        // Trigger input event to resize textarea (if applicable)
                        inputField.dispatchEvent(new Event('input'));
                    }
                });
            });

            // Listen for the custom event for loading recommended tools
            document.addEventListener('loadRecommendedTools', (event) => {
                const agentData = event.detail;
                // Check if we're in multi-agent mode with data
                if (isMultiAgentMode && multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                    // Use the multiAgentData directly in multi-agent mode
                    this.loadMCPHubTools(multiAgentData);
                } else if (agentData && (agentData.agent_name || agentData.description || agentData.keywords)) {
                    // Single agent mode - use the provided agent data
                    this.loadMCPHubTools(agentData);
                }
            });
        },

        async loadAvailableFields() {
            try {
                // Get all field information in a single API call
                const fieldMetadata = await ApiService.getFieldMetadata();

                // Extract available fields and their descriptions from the single response
                availableFields = fieldMetadata.fields || [];

                // Create field descriptions array with the data we received
                const fieldDescriptions = availableFields.map(field => ({
                    name: field,
                    description: fieldMetadata.descriptions?.[field] || 'No description available.'
                }));

                UiManager.updateFieldDescriptions(fieldDescriptions);
            } catch (error) {
                console.error('Error loading field information:', error);
                Utils.showNotification('Error loading field information. Using default fields.', 'warning');
            }
        },

        async loadAvailableTools() {
            try {
                // Get available tools
                console.log('Starting to load available tools...');
                const tools = await ApiService.getAvailableTools();

                // Tools are already stored globally by ApiService.getAvailableTools
                console.log(`Successfully loaded ${tools.length} tools for agent creation`);
                return tools;
            } catch (error) {
                console.error('Error loading available tools:', error);
                Utils.showNotification('Error loading available tools. Some functionality may be limited.', 'warning');

                // Retry after a short delay (3 seconds)
                console.log('Scheduling retry for tool loading...');
                setTimeout(() => {
                    this.retryLoadTools();
                }, 3000);

                return [];
            }
        },

        async retryLoadTools() {
            try {
                console.log('Retrying tool loading...');
                const tools = await ApiService.getAvailableTools();

                console.log(`Successfully loaded ${tools.length} tools on retry`);

                // If we're displaying the agent preview with tools, update it
                if (extractedAgentData && extractedAgentData.tools) {
                    UiManager.updateAgentPreview(extractedAgentData);
                }

                return tools;
            } catch (error) {
                console.error('Retry failed to load tools:', error);
                return [];
            }
        },

        async handleUserInput() {
            if (isProcessing) return;

            const userInput = UiManager.getUserInput();
            if (!userInput) return;

            // Add user message to chat
            UiManager.addUserMessage(userInput);
            UiManager.clearUserInput();

            // Set processing state
            isProcessing = true;
            UiManager.addBotTypingIndicator();

            try {
                // Get model settings
                const { model, temperature, isMultiAgent } = UiManager.getModelSettings();

                // Set the global multi-agent mode flag
                isMultiAgentMode = isMultiAgent;

                // Process the user input - choose whether to use multi-agent or standard parsing
                if (isMultiAgentMode) {
                    await this.processMultiAgentInput(userInput, model, temperature);
                } else {
                    await this.processUserInput(userInput, model, temperature);
                }

                // Update button state based on data
                const hasRequiredFields = isMultiAgentMode ?
                    (multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) :
                    DataProcessor.hasRequiredFields(extractedAgentData);

                UiManager.updateCreateButtonState(hasRequiredFields);
            } catch (error) {
                // Handle error
                UiManager.removeTypingIndicator();
                UiManager.addBotMessage("I'm sorry, I encountered an error processing your request. Please try again.");
                Utils.showNotification(`Error: ${error.message || 'Unknown error'}`, 'danger');
            } finally {
                isProcessing = false;
            }
        },

        async processUserInput(userInput, model, temperature) {
            try {
                // Ensure tools are loaded
                if (!window.availableTools || window.availableTools.length === 0) {
                    await this.loadAvailableTools();
                }

                // Get stream URL for user input parsing
                const streamUrl = ApiService.getParseStreamUrl();
                console.log('Using streaming endpoint:', streamUrl);

                // Create the request body
                const requestBody = {
                    user_input: userInput,
                    model_name: model,
                    temperature: temperature
                };

                if (Object.keys(extractedAgentData).length > 0) {
                    requestBody.existing_field_values = extractedAgentData;
                }

                // Reset processed fields to track what we've received in the stream
                const processedFields = {};
                const accumulatedFields = {};

                try {
                    // Create headers with authorization
                    const headers = {
                        'Content-Type': 'application/json',
                        'Accept': 'text/event-stream',
                        ...API.getHeaders()
                    };

                    // Make the streaming request
                    const response = await fetch(streamUrl, {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(requestBody)
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    // Create a reader for the stream
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    let fieldUpdateReceived = false;

                    // Process the stream
                    while (true) {
                        const { done, value } = await reader.read();

                        if (done) {
                            console.log('Stream complete');
                            break;
                        }

                        // Decode the chunk and add it to the buffer
                        buffer += decoder.decode(value, { stream: true });

                        // Process complete events in the buffer
                        let eventEnd = buffer.indexOf('\n\n');
                        while (eventEnd > -1) {
                            const eventData = buffer.substring(0, eventEnd);
                            buffer = buffer.substring(eventEnd + 2);

                            // Process the event
                            const eventProcessed = this.processStreamEvent(
                                eventData,
                                processedFields,
                                accumulatedFields
                            );

                            if (eventProcessed) {
                                fieldUpdateReceived = true;
                            }

                            // Look for the next event
                            eventEnd = buffer.indexOf('\n\n');
                        }
                    }

                    // If we didn't receive any field updates, fall back to non-streaming method
                    if (!fieldUpdateReceived) {
                        console.log('No field updates received from stream');
                        UiManager.removeTypingIndicator();
                        console.log('Raw buffer content:', buffer);

                        // Show more descriptive error if we have raw content that failed to parse
                        let errorMessage = "I couldn't extract structured architecture from your description. ";
                        if (buffer && buffer.trim().length > 0) {
                            errorMessage += "The neural link returned raw data that doesn't fit the expected blueprint format. \n\n" +
                                "<strong>Raw Transmission:</strong><br><div class='p-2 bg-dark rounded mt-2 border border-secondary small opacity-75' style='max-height: 200px; overflow-y: auto;'>" +
                                buffer + "</div>\n\n" +
                                "Please try specifying the agent name and description more clearly.";
                        } else {
                            errorMessage += "The extraction matrix returned null content. Please provide a more detailed mission statement for the agent.";
                        }

                        UiManager.addBotMessage(errorMessage);
                        return;
                    } else {
                        // Update extractedAgentData with all accumulated fields
                        for (const [field, value] of Object.entries(accumulatedFields)) {
                            if (value) {
                                if (field === 'tools') {
                                    // Handle tools field specially
                                    extractedAgentData.tools = DataProcessor.processToolsValue(value);
                                } else {
                                    extractedAgentData[field] = value;
                                }
                            }
                        }

                        // Always set on_status to true regardless of what was extracted
                        extractedAgentData.on_status = true;
                    }
                } catch (error) {
                    console.error('Error in streaming request:', error);
                    throw error;
                }

                // Extract keywords first if we have name and description
                if (extractedAgentData.agent_name && extractedAgentData.description) {
                    try {
                        const keywordsResponse = await ApiService.makeRequest('/user-input/extract-keywords', 'POST', {
                            agent_name: extractedAgentData.agent_name,
                            description: extractedAgentData.description,
                            model_name: model,
                            temperature: temperature
                        });

                        if (keywordsResponse && Array.isArray(keywordsResponse.keywords)) {
                            extractedAgentData.keywords = keywordsResponse.keywords;
                        }
                    } catch (error) {
                        console.warn('Error extracting keywords:', error);
                        extractedAgentData.keywords = ['automation', 'helper', 'assistant'];
                    }
                }

                // Then autofill tools
                await this.autofillTools();

                // Generate response showing what was extracted
                // Tempat mengisi field yang sudah diisi
                const botResponse = DataProcessor.generateResponseFromExtractedData(extractedAgentData);

                // Update UI
                UiManager.removeTypingIndicator();
                UiManager.addBotMessage(botResponse);
                UiManager.updateAgentPreview(extractedAgentData);

                // Trigger recommendation loading
                if (extractedAgentData.agent_name || extractedAgentData.description) {
                    const event = new CustomEvent('loadRecommendedTools', { detail: extractedAgentData });
                    document.dispatchEvent(event);
                }
            } catch (error) {
                console.error('Error processing user input:', error);
                UiManager.removeTypingIndicator();
                UiManager.addBotMessage("I'm sorry, I encountered an error processing your request. Please try again.");
                throw error;
            }
        },

        processStreamEvent(eventData, processedFields, accumulatedFields) {
            // Split the event into lines
            const lines = eventData.split('\n');
            let eventType = '';
            let data = '';

            // Parse the event
            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventType = line.substring(6).trim();
                } else if (line.startsWith('data:')) {
                    data = line.substring(5).trim();
                }
            }

            // Skip if no data
            if (!data) {
                return false;
            }

            // If data is [DONE], we're done
            if (data === '[DONE]') {
                console.log('Stream finished');
                return false;
            }

            try {
                // Parse the data as JSON
                const jsonData = JSON.parse(data);

                if (eventType === 'field_update') {
                    // Process field update event
                    for (const [field, value] of Object.entries(jsonData)) {
                        // Track that we've processed this field
                        processedFields[field] = true;

                        // Update accumulated field data
                        accumulatedFields[field] = value;

                        // Update extractedAgentData in real-time
                        if (field === 'tools') {
                            extractedAgentData.tools = DataProcessor.processToolsValue(value);
                        } else {
                            extractedAgentData[field] = value;
                        }

                        // Always set on_status to true
                        extractedAgentData.on_status = true;

                        // Update UI in real-time - pass the isMultiAgentMode flag to maintain multi-agent view
                        UiManager.updateAgentPreview(extractedAgentData, isMultiAgentMode);
                    }
                    return true;
                }

                return false;
            } catch (error) {
                console.error('Error processing stream event:', error, eventData);
                return false;
            }
        },


        async autofillTools() {
            try {
                console.log('Starting autofillTools method');
                isToolsAutofilling = true;
                UiManager.updateToolAutofillStatus(true);
                UiManager.updateAgentPreview(extractedAgentData, isMultiAgentMode);

                // Only proceed if we have available tools
                if (!window.availableTools?.length) {
                    console.log('No available tools loaded yet, delaying autofill');
                    return;
                }

                // Function to get tool suggestions for an agent
                const getToolSuggestions = async (agentData) => {
                    try {
                        const toolsAutofillData = await ApiService.autofillField(
                            'tools',
                            {
                                ...agentData,
                                keywords: agentData.keywords || []
                            },
                            ''
                        );
                        return DataProcessor.processToolsValue(toolsAutofillData.autofilled_value);
                    } catch (error) {
                        console.warn('Error getting tool suggestions:', error);
                        return [];
                    }
                };

                // Function to update tool checkboxes
                const updateToolCheckboxes = (toolIds, containerId = 'tool-checkboxes-container') => {
                    const container = document.getElementById(containerId);
                    if (!container) return;

                    // First unselect all tools
                    container.querySelectorAll('.tool-checkbox').forEach(checkbox => {
                        checkbox.checked = false;
                        checkbox.dispatchEvent(new Event('change'));
                    });

                    // Then select recommended tools
                    toolIds.forEach(toolId => {
                        const checkbox = container.querySelector(`#tool-${toolId}`);
                        if (checkbox) {
                            checkbox.checked = true;
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    });
                };

                if (isMultiAgentMode && multiAgentData?.agent_variations?.length) {
                    // Process all agents in parallel
                    await Promise.all(multiAgentData.agent_variations.map(async (agent, index) => {
                        // Get agent-specific keywords or fall back to common ones
                        const agentData = {
                            agent_name: agent.agent_name || multiAgentData.common_attributes?.agent_name,
                            description: agent.description || multiAgentData.common_attributes?.description,
                            keywords: agent.keywords || multiAgentData.common_attributes?.keywords || []
                        };

                        const suggestedTools = await getToolSuggestions(agentData);
                        multiAgentData.agent_variations[index].tools = suggestedTools;

                        // Update UI for this agent's tools
                        updateToolCheckboxes(suggestedTools, `agent-${index}-tool-checkboxes-container`);
                    }));
                } else {
                    // Single agent mode
                    const suggestedTools = await getToolSuggestions(extractedAgentData);
                    extractedAgentData.tools = suggestedTools;
                    updateToolCheckboxes(suggestedTools);
                }
            } catch (error) {
                console.warn('Error in autofillTools:', error);
            } finally {
                isToolsAutofilling = false;
                UiManager.updateToolAutofillStatus(false);
                UiManager.updateAgentPreview(extractedAgentData, isMultiAgentMode);
            }
        },

        async autofillAgentVariationTools() {
            console.log('Autofilling tools for agent variations');

            try {
                // Set autofilling status for multi-agent mode
                isToolsAutofilling = true;
                UiManager.updateToolAutofillStatus(true);
                UiManager.updateAgentPreview(extractedAgentData, true);

                // Process each agent variation
                for (let i = 0; i < multiAgentData.agent_variations.length; i++) {
                    const agent = multiAgentData.agent_variations[i];

                    // Only proceed if we have agent name or description
                    if (!agent.agent_name && !agent.description) continue;

                    console.log(`Autofilling tools for agent variation ${i}: ${agent.agent_name}`);

                    try {
                        // Use agent-specific keywords if available, otherwise fall back to common keywords
                        const agentKeywords = agent.keywords && Array.isArray(agent.keywords) && agent.keywords.length > 0
                            ? agent.keywords
                            : (multiAgentData.common_attributes.keywords || []);

                        // Build agent data for autofill request
                        const agentData = {
                            agent_name: agent.agent_name || multiAgentData.common_attributes.agent_name || '',
                            description: agent.description || multiAgentData.common_attributes.description || '',
                            keywords: agentKeywords
                        };

                        // Get tool recommendations for this agent
                        const toolsAutofillData = await ApiService.autofillField('tools', agentData, '');

                        // Process the tools suggestion
                        let suggestedTools = DataProcessor.processToolsValue(toolsAutofillData.autofilled_value);

                        // Update the agent variation data with recommended tools
                        multiAgentData.agent_variations[i].tools = suggestedTools;

                        console.log(`Suggested tools for agent ${i} (${agent.agent_name}):`, suggestedTools);
                    } catch (error) {
                        console.warn(`Error autofilling tools for agent ${i}:`, error);
                        // Use empty tools array if autofill fails
                        multiAgentData.agent_variations[i].tools = [];
                    }
                }

                // Update UI for each agent's tools
                for (let i = 0; i < multiAgentData.agent_variations.length; i++) {
                    UiManager.populateAgentToolCheckboxes(i, multiAgentData.agent_variations[i].tools || []);
                }

                // Update autofill status and UI
                isToolsAutofilling = false;
                UiManager.updateToolAutofillStatus(false);
                UiManager.updateAgentPreview(extractedAgentData, true);

            } catch (error) {
                console.warn('Error autofilling agent variation tools:', error);
                // Reset autofilling state on error
                isToolsAutofilling = false;
                UiManager.updateToolAutofillStatus(false);
                UiManager.updateAgentPreview(extractedAgentData, true);
            }
        },

        resetAgentData() {
            extractedAgentData = {};
            multiAgentData = null;
            isMultiAgentMode = false;

            // Reset UI
            UiManager.clearChat();
            UiManager.updateAgentPreview({});
            UiManager.updateCreateButtonState(false);

            // Reset multi-agent toggle
            document.getElementById('multi-agent-toggle').checked = false;
        },

        async createAgent() {
            if (isMultiAgentMode && multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                return this.createMultipleAgents();
            }

            if (Object.keys(extractedAgentData).length === 0) {
                Utils.showNotification("No agent data to create", "warning");
                return;
            }

            try {
                // Ensure we have the latest selection of tools from the UI
                this.updateToolSelectionFromUI();

                // Prepare agent data
                const agentData = DataProcessor.prepareAgentDataForCreation(extractedAgentData);

                console.log('Creating agent with data:', agentData);

                // Call API to create agent
                await API.post('/agents', agentData);

                // Show success message
                Utils.showNotification(`Agent "${agentData.agent_name}" created successfully!`, "success");
                UiManager.addBotMessage(`Great! I've created your agent "${agentData.agent_name}" with ${agentData.tools.length} tools. You can now find it in the Agents list.`);

                // Reset after a short delay
                setTimeout(() => {
                    this.resetAgentData();
                }, 3000);
            } catch (error) {
                console.error('Error creating agent:', error);
                Utils.showNotification(`Error creating agent: ${error.message || 'Unknown error'}`, 'danger');
                UiManager.addBotMessage("There was an error creating your agent. Please try again or check the console for more details.");
            }
        },

        updateToolSelectionFromUI() {
            // Get all selected tools from the checkboxes
            const selectedTools = Array.from(
                document.querySelectorAll('.tool-checkbox:checked')
            ).map(cb => cb.value);

            console.log('Final tool selection for agent creation:', selectedTools);

            // Update the extracted agent data
            extractedAgentData.tools = selectedTools;

            return selectedTools;
        },

        addToolSelectionStyles() {
            // Create a style element
            const style = document.createElement('style');

            // Define the CSS styles
            style.textContent = `
                .tool-selection-container {
                    max-height: 300px;
                    overflow-y: auto;
                    padding: 10px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                }
                
                .agent-tool-checkboxes {
                    max-height: 250px;
                    overflow-y: auto;
                    padding: 5px;
                    border: 1px solid #ffeeba;
                    border-radius: 5px;
                    background-color: #fffdf5;
                }
                
                .recommended-tools-container {
                    max-height: 300px;
                    overflow-y: auto;
                    padding: 10px;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                }
                
                .mcphub-tools-container {
                    max-height: 300px;
                    overflow-y: auto;
                    padding: 10px;
                    border: 1px solid #d1e7dd;
                    border-radius: 5px;
                    background-color: #f0f9f6;
                }
                
                .mcphub-tools-container .list-group-item {
                    border-left: 4px solid #20c997;
                }
                
                .mcphub-tools-container .badge {
                    background-color: #20c997;
                }
                
                .tool-checkboxes {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 8px;
                }
                
                .form-check {
                    padding: 8px;
                    border-radius: 4px;
                    transition: background-color 0.2s;
                }
                
                .form-check:hover {
                    background-color: rgba(0, 123, 255, 0.1);
                }
                
                .form-check-input:checked + .form-check-label {
                    font-weight: 500;
                    color: #0d6efd;
                }
                
                .agent-tool-checkbox-item .form-check-input:checked + .form-check-label {
                    color: #fd7e14;
                }
                
                .agent-preview-container {
                    padding: 15px;
                }
                
                .field-item {
                    margin-bottom: 10px;
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                }
                
                .field-item--filled {
                    background-color: #e9f7ef;
                }
                
                .field-item--agent-specific {
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                }
                
                .tools-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }
                
                .tools-actions {
                    display: flex;
                    gap: 10px;
                }
                
                .loading-indicator {
                    display: flex;
                    align-items: center;
                    padding: 10px;
                    color: #6c757d;
                }
                
                .list-group-item .badge {
                    margin-left: 8px;
                }
                
                /* New styles for autofill indicator */
                .autofill-status {
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    font-size: 0.875rem;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                
                .autofill-status.autofilling {
                    color: #0d6efd;
                    background-color: rgba(13, 110, 253, 0.1);
                }
                
                .autofill-status.complete {
                    color: #198754;
                    background-color: rgba(25, 135, 84, 0.1);
                }
                
                .spin {
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `;

            // Append the style element to the head
            document.head.appendChild(style);
        },

        async loadMCPHubTools(agentData) {
            const mcphubToolsContainer = document.getElementById('mcphub-tools-container');
            if (!mcphubToolsContainer) {
                console.error('Cannot find MCPHub tools container element');
                return;
            }

            try {
                console.log('Loading MCPHub tool recommendations for:', agentData);

                // Show loading indicator (already present in HTML)

                // Prepare keyword data - collect all keywords when in multi-agent mode
                let allKeywords = [];

                if (isMultiAgentMode && multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                    console.log('Multi-agent mode detected - collecting keywords from all variations');

                    // Start with common keywords if available
                    if (multiAgentData.common_attributes && multiAgentData.common_attributes.keywords) {
                        allKeywords = [...multiAgentData.common_attributes.keywords];
                    }

                    // Add keywords from each agent variation
                    multiAgentData.agent_variations.forEach(agent => {
                        if (agent.keywords && Array.isArray(agent.keywords) && agent.keywords.length > 0) {
                            allKeywords = [...allKeywords, ...agent.keywords];
                        }
                    });

                    // Remove duplicates
                    allKeywords = [...new Set(allKeywords)];

                    console.log('Combined unique keywords from all agents:', allKeywords);
                } else {
                    // Single agent mode - use keywords from agent data
                    allKeywords = agentData.keywords || [];
                }

                // Prepare request data
                const requestData = {
                    field_name: 'mcphub_recommended_tools',
                    json_field: {
                        keywords: allKeywords // Use the combined keywords list
                    },
                    existing_field_value: '',
                    available_tools: [],
                    return_tool_ids: false
                };

                console.log('Fetching MCPHub tool recommendations with data:', requestData);

                // Make request to the backend
                const response = await ApiService.makeRequest('/agent-creator-autofill/invoke', 'POST', requestData);

                console.log('MCPHub recommendations response:', response);

                // Handle the response
                if (response && response.autofilled_value) {
                    let recommendedTools = [];

                    // Parse the response
                    if (typeof response.autofilled_value === 'string') {
                        try {
                            recommendedTools = JSON.parse(response.autofilled_value);
                        } catch (e) {
                            console.warn('Error parsing MCPHub JSON:', e);
                            // Use defaults if parsing fails
                            recommendedTools = [
                                { "name": "GitHub Tools", "description": "GitHub integration", "url": "https://github.com" },
                                { "name": "Google Calendar", "description": "Calendar integration", "url": "https://calendar.google.com" }
                            ];
                        }
                    } else if (Array.isArray(response.autofilled_value)) {
                        recommendedTools = response.autofilled_value;
                    }

                    console.log('Parsed MCPHub tools:', recommendedTools);

                    // Only update agent preview in multi-agent mode if needed
                    // Remove the conditional to ensure we always update the UI regardless
                    // of multi-agent mode state

                    // Render the recommended tools regardless of multi-agent mode
                    if (recommendedTools.length > 0) {
                        let toolsHtml = '<ul class="list-group">';

                        recommendedTools.forEach(tool => {
                            // Get tool properties
                            const toolName = tool.name || 'Unknown Tool';
                            const toolDescription = tool.description || 'No description available';
                            const toolUrl = tool.url || '#';

                            toolsHtml += `
                                <li class="list-group-item d-flex justify-content-between align-items-start">
                                    <div class="ms-2 me-auto">
                                        <div class="fw-bold">${toolName}</div>
                                        ${toolDescription}
                                    </div>
                                    <a href="${toolUrl}" target="_blank" class="badge bg-primary rounded-pill">MCPHub</a>
                                </li>
                            `;
                        });

                        toolsHtml += '</ul>';
                        mcphubToolsContainer.innerHTML = toolsHtml;

                        // Make sure container is visible
                        mcphubToolsContainer.style.display = 'block';
                    } else {
                        // No recommended tools
                        mcphubToolsContainer.innerHTML = `
                            <div class="alert alert-info">
                                No specific MCPHub tools found for this agent description.
                            </div>
                        `;
                    }

                } else {
                    // No valid response
                    mcphubToolsContainer.innerHTML = `
                        <div class="alert alert-warning">
                            Couldn't get MCPHub recommendations. Try providing more details in your agent description.
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error loading MCPHub recommendations:', error);

                // Log detailed error information
                if (error.status) console.error('Status:', error.status);
                if (error.detail) console.error('Detail:', error.detail);
                if (error.message) console.error('Message:', error.message);

                // Show error message in UI
                if (mcphubToolsContainer) {
                    mcphubToolsContainer.innerHTML = `
                        <div class="alert alert-danger">
                            Error loading MCPHub recommendations: ${error.message || error.detail || 'Unknown error'}
                        </div>
                    `;
                }

                // Ensure multi-agent view is restored if needed
                if (isMultiAgentMode && multiAgentData && multiAgentData.agent_variations && multiAgentData.agent_variations.length > 0) {
                    setTimeout(() => {
                        UiManager.updateAgentPreview(extractedAgentData, true);
                    }, 100);
                }
            }
        },

        async processMultiAgentInput(userInput, model, temperature) {
            try {
                // Ensure tools are loaded
                if (!window.availableTools || window.availableTools.length === 0) {
                    await this.loadAvailableTools();
                }

                // Create the request body
                const requestBody = {
                    user_input: userInput,
                    model_name: model,
                    temperature: temperature,
                    existing_data: Object.keys(extractedAgentData).length > 0 ? extractedAgentData : null
                };

                // Make request to parse multi-agent input
                const multiAgentResponse = await ApiService.makeRequest('/user-input/parse-multi-agent', 'POST', requestBody);
                console.log('Multi-agent parse response:', multiAgentResponse);

                // Normalize agent data structure
                this.normalizeAgentData(multiAgentResponse);

                // Store the multi-agent data
                multiAgentData = multiAgentResponse;

                // Handle special cases
                if (multiAgentResponse.need_more_info) {
                    UiManager.removeTypingIndicator();
                    UiManager.addBotMessage(`I need more information about the agents you want to create. ${multiAgentResponse.missing_info || 'Please provide details about each agent and how they differ.'}`);
                    return;
                }

                if (!multiAgentResponse.has_multi_agent) {
                    UiManager.addBotMessage("I couldn't detect multiple agents in your description. Switching to single agent mode.");
                    return await this.processUserInput(userInput, model, temperature);
                }

                // Update common attributes
                Object.assign(extractedAgentData, multiAgentResponse.common_attributes || {});

                // Extract keywords for all agents in parallel
                await this.extractKeywordsForAllAgents(multiAgentResponse, model, temperature);

                // Generate and display response
                const botResponse = this.generateMultiAgentResponse(multiAgentResponse);
                UiManager.removeTypingIndicator();
                UiManager.addBotMessage(botResponse);
                UiManager.updateAgentPreview(extractedAgentData, true);

                // Autofill tools and trigger recommendations
                await this.autofillTools();

                if (multiAgentData?.agent_variations?.length > 0) {
                    document.dispatchEvent(new CustomEvent('loadRecommendedTools', { detail: multiAgentData }));
                }

            } catch (error) {
                console.error('Error processing multi-agent input:', error);
                UiManager.removeTypingIndicator();
                UiManager.addBotMessage("I'm sorry, I encountered an error processing your multi-agent request. Please try again.");
                throw error;
            }
        },

        // Helper method to normalize agent data structure
        normalizeAgentData(response) {
            if (response.common_attributes?.agent_style) {
                response.common_attributes.agent_name = response.common_attributes.agent_style;
                delete response.common_attributes.agent_style;
            }

            if (response.agent_variations) {
                response.agent_variations.forEach(agent => {
                    if (agent.agent_style && !agent.agent_name) {
                        agent.agent_name = agent.agent_style;
                        delete agent.agent_style;
                    }
                    if (!agent.tools) {
                        agent.tools = [];
                    }
                });
            }
        },

        // Helper method to extract keywords for all agents
        async extractKeywordsForAllAgents(response, model, temperature) {
            const extractKeywords = async (name, description) => {
                try {
                    const keywordsResponse = await ApiService.makeRequest('/user-input/extract-keywords', 'POST', {
                        agent_name: name,
                        description: description,
                        model_name: model,
                        temperature: temperature
                    });
                    return keywordsResponse?.keywords || ['automation', 'helper', 'assistant'];
                } catch (error) {
                    console.warn('Error extracting keywords:', error);
                    return ['automation', 'helper', 'assistant'];
                }
            };

            // Extract common keywords if needed
            if (response.common_attributes?.agent_name && response.common_attributes?.description) {
                const commonKeywords = await extractKeywords(
                    response.common_attributes.agent_name,
                    response.common_attributes.description
                );
                response.common_attributes.keywords = commonKeywords;
                extractedAgentData.keywords = commonKeywords;
            }

            // Extract keywords for variations in parallel
            if (response.agent_variations) {
                await Promise.all(response.agent_variations.map(async (agent) => {
                    if (agent.agent_name && agent.description) {
                        agent.keywords = await extractKeywords(agent.agent_name, agent.description);
                    } else {
                        agent.keywords = response.common_attributes?.keywords || ['automation', 'helper', 'assistant'];
                    }
                }));
            }
        },

        // Helper method to generate response message
        generateMultiAgentResponse(response) {
            const formatField = (field, value) => {
                if (field === 'keywords' && Array.isArray(value)) {
                    return `   • ${field}: ${value.join(', ')}\n`;
                }
                return value && typeof value !== 'object' ? `   • ${field}: ${value}\n` : '';
            };

            let botResponse = `I've detected ${response.agent_count} distinct entities within your description.\n\n`;

            // Add common attributes
            const commonFields = Object.entries(response.common_attributes || {}).filter(([_, v]) => v && v !== "");
            if (commonFields.length > 0) {
                botResponse += "**Shared Architecture Blueprint:**\n";
                commonFields.forEach(([field, value]) => {
                    botResponse += formatField(field, value);
                });
                botResponse += "\n";
            }

            // Add agent variations
            botResponse += "**Individual Module Variations:**\n";
            response.agent_variations.forEach((agent, index) => {
                const agentName = agent.agent_name || response.common_attributes?.agent_name || `Agent ${index + 1}`;
                botResponse += `\n**Entity ${index + 1}: ${agentName}**\n`;

                Object.entries(agent).forEach(([field, value]) => {
                    // Only show field if it's not already in common_attributes or if it's different
                    if (value && (!response.common_attributes?.[field] || response.common_attributes[field] !== value)) {
                        botResponse += formatField(field, value);
                    }
                });
            });

            botResponse += "\nNeural link matrices are visible in the inspector. Should we proceed with multi-agent compile?";
            return botResponse;
        },

        async createMultipleAgents() {
            try {
                // Prepare agent data for each variation
                const agents = DataProcessor.prepareMultiAgentDataForCreation(
                    multiAgentData.common_attributes,
                    multiAgentData.agent_variations
                );

                // No need to add tools to each agent here as they are already included
                // from the agent_variations data (each agent has its own tools)

                console.log('Creating multiple agents:', agents);

                // Show creating message
                UiManager.addBotMessage(`Creating ${agents.length} agents...`);

                // Create each agent sequentially
                const results = [];
                for (let i = 0; i < agents.length; i++) {
                    const agentData = agents[i];
                    try {
                        // Call API to create agent
                        const response = await API.post('/agents', agentData);
                        results.push({
                            success: true,
                            name: agentData.agent_name,
                            data: response
                        });
                    } catch (error) {
                        console.error(`Error creating agent ${i + 1}:`, error);
                        results.push({
                            success: false,
                            name: agentData.agent_name,
                            error: error.message || 'Unknown error'
                        });
                    }
                }

                // Generate response based on results
                const successCount = results.filter(r => r.success).length;

                let responseMessage = `Created ${successCount} out of ${agents.length} agents:\n\n`;
                results.forEach((result, index) => {
                    const toolCount = agents[index].tools ? agents[index].tools.length : 0;
                    responseMessage += `${index + 1}. ${result.name}: ${result.success ? `✅ Success (${toolCount} tools)` : '❌ Failed - ' + result.error}\n`;
                });

                // Show success message
                if (successCount === agents.length) {
                    Utils.showNotification(`All ${agents.length} agents created successfully!`, "success");
                } else if (successCount > 0) {
                    Utils.showNotification(`Created ${successCount} out of ${agents.length} agents`, "warning");
                } else {
                    Utils.showNotification("Failed to create any agents", "danger");
                }

                UiManager.addBotMessage(responseMessage);

                // Reset after a short delay
                setTimeout(() => {
                    this.resetAgentData();
                }, 3000);
            } catch (error) {
                console.error('Error creating multiple agents:', error);
                Utils.showNotification(`Error creating agents: ${error.message || 'Unknown error'}`, 'danger');
                UiManager.addBotMessage("There was an error creating your agents. Please try again or check the console for more details.");
            }
        }
    };

    // Public API
    return {
        init: () => Controller.init()
    };
})();

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    AgentCreator.init();
});