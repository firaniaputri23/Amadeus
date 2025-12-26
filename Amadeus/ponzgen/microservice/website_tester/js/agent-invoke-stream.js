/**
 * Agent Invoke Stream JavaScript file
 * Handles agent invocation with streaming responses and Image Uploads
 */

// Current agent details stored globally
let currentAgentDetails = null;
let eventSource = null;
// Store the selected image data
let selectedImage = null;

// Use the API utility to get the base URL
function getInvokeApiUrl() {
    // For backward compatibility, use API.getBaseUrl() instead of a separate URL
    return API.getBaseUrl();
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function () {
    // Load agents for the dropdown
    loadAgentsForDropdown();

    // Load available LLM models
    loadAvailableModels();

    // Event listeners
    document.getElementById('agent-select').addEventListener('change', updateAgentSelection);
    document.getElementById('get-agent-info').addEventListener('click', getAgentInfo);

    // Updated: invokeAgentStream handles both text and images
    document.getElementById('invoke-agent').addEventListener('click', invokeAgentStream);

    document.getElementById('clear-response').addEventListener('click', clearResponse);
    document.getElementById('update-settings').addEventListener('click', function () {
        Utils.showNotification('Settings updated', 'success');
    });

    // Add event listener for Enter key in the message input
    document.getElementById('agent-message').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            invokeAgentStream();
        }
    });

    // --- NEW: Image Upload Listeners ---
    document.getElementById('image-upload').addEventListener('change', handleImageUpload);
    document.getElementById('remove-image').addEventListener('click', removeSelectedImage);
});

// --- NEW: Image Handling Functions ---

// Handle image file selection
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        selectedImage = {
            data: e.target.result, // Base64 string
            name: file.name,
            type: file.type
        };

        // Show preview in the UI
        document.getElementById('preview-image').src = e.target.result;
        document.getElementById('image-preview').style.display = 'block';
    };
    reader.readAsDataURL(file);

    // Reset the input to allow selecting the same file again if needed
    event.target.value = '';
}

// Remove the selected image
function removeSelectedImage() {
    selectedImage = null;
    document.getElementById('image-preview').style.display = 'none';
    document.getElementById('preview-image').src = '#';
    document.getElementById('image-upload').value = '';
}

// ---------------------------------------------------------

// Load available LLM models
async function loadAvailableModels() {
    const modelSelect = document.getElementById('model-name');

    try {
        // Fetch available models from the backend
        const response = await fetch(`${getInvokeApiUrl()}/get-llms`);
        const data = await response.json();

        if (!data.available_models || data.available_models.length === 0) {
            modelSelect.innerHTML = '<option value="custom-vlm" selected>Custom VLM (Default)</option>';
            console.log('No models available from backend, using default');
            return;
        }

        const modelInfo = data.model_info || {};

        // Define Categories and Colors
        const categories = {
            'Anthropic': { prefix: ['anthropic/', 'maia/claude'], color: '#ff6b6b', models: [] }, // Red
            'Deepseek': { prefix: ['deepseek/', 'maia/deepseek'], color: '#ffa500', models: [] },  // Orange
            'Google': { prefix: ['maia/gemini', 'maia/google', 'google/', 'custom-vlm'], color: '#ffd700', models: [] },   // Yellow
            'Mistral': { prefix: ['mistral/', 'maia/mistral'], color: '#4caf50', models: [] },    // Green
            'Moonshot': { prefix: ['moonshot/', 'maia/moonshot'], color: '#e040fb', models: [] }, // Purple
            'OpenAI': { prefix: ['openai/', 'maia/gpt', 'maia/openai'], color: '#4da6ff', models: [] }       // Blue
        };

        const otherModels = [];

        // Sort models into categories
        data.available_models.forEach(modelName => {
            let placed = false;
            // Iterate manually to ensure specific logic if needed, but the loop is fine if prefixes are distinctive
            for (const [catName, catData] of Object.entries(categories)) {
                if (catData.prefix.some(p => modelName.startsWith(p) || modelName === p)) {
                    catData.models.push(modelName);
                    placed = true;
                    break;
                }
            }
            // Fallback for generic 'maia/' if not caught above (default to Google/Maia if strictly maia/ but not sub-categorized)
            if (!placed && modelName.startsWith('maia/')) {
                categories['Google'].models.push(modelName);
                placed = true;
            }

            if (!placed) {
                otherModels.push(modelName);
            }
        });

        // Helper to create options
        const createOption = (modelName) => {
            const info = modelInfo[modelName] || {};
            const isFree = info.cost && (info.cost.includes('free') || info.cost.includes('FREE'));
            const toolCalling = info.tool_calling ? '🔧' : '';
            const vision = info.vision ? '👁️' : '';
            const freeTag = isFree ? ' [FREE]' : '';

            let label = `${toolCalling}${vision} ${modelName}${freeTag}`;

            // Mark recommended models
            const isRecommended = data.recommendations &&
                (data.recommendations.tool_calling_free === modelName ||
                    data.recommendations.default_for_mcp === modelName);

            if (isRecommended) {
                label = `⭐ ${label}`;
            }

            // Determine if selected
            let selected = '';
            const defaultModel = data.recommendations && data.recommendations.default_for_mcp
                ? data.recommendations.default_for_mcp
                : 'custom-vlm';

            if (modelName === defaultModel) {
                selected = 'selected';
            } else if (!data.available_models.includes(defaultModel) && modelName === 'custom-vlm') {
                selected = 'selected';
            }

            return `<option value="${modelName}" ${selected} style="color: inherit;">${label}</option>`;
        };

        let finalHtml = '';

        // Iterate categories ensuring explicit order
        const categoryOrder = ['Anthropic', 'Deepseek', 'Google', 'Mistral', 'Moonshot', 'OpenAI'];

        categoryOrder.forEach(catName => {
            const catData = categories[catName];
            if (catData.models.length > 0) {
                // Style the optgroup label
                finalHtml += `<optgroup label="${catName}" style="color: ${catData.color}; font-weight: bold;">`;
                catData.models.forEach(m => {
                    finalHtml += createOption(m);
                });
                finalHtml += `</optgroup>`;
            }
        });

        // Add Others if any
        if (otherModels.length > 0) {
            finalHtml += `<optgroup label="Other" style="color: #ffffff;">`;
            otherModels.forEach(m => {
                finalHtml += createOption(m);
            });
            finalHtml += `</optgroup>`;
        }

        modelSelect.innerHTML = finalHtml;
        console.log(`Loaded ${data.available_models.length} models into categories.`);

    } catch (error) {
        console.error('Error loading models:', error);
        modelSelect.innerHTML = '<option value="custom-vlm" selected>Custom VLM (Default)</option>';
    }
}

// Load agents for the dropdown
async function loadAgentsForDropdown() {
    try {
        console.log('Loading agents for dropdown...');

        // Use the API utility for making the request with proper authentication
        const agents = await API.get('/agents');

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

// Update agent selection when agent is selected
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

        // Use the API utility for making the request with proper authentication
        const agentDetails = await API.get(`/agents/${agentId}`);

        // Store agent details globally for use in invoke function
        currentAgentDetails = agentDetails;

        // Display agent details
        let infoHtml = `
            <div class="agent-summary-card">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="text-white mb-0" style="letter-spacing: 0.5px;">${agentDetails.agent_name}</h6>
                    <span class="badge bg-transparent border ${agentDetails.on_status ? 'border-success text-success' : 'border-secondary text-secondary'} " style="font-size: 0.6rem;">
                        ${agentDetails.on_status ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                </div>
                <p class="small text-white opacity-75 mb-3" style="font-size: 0.8rem; line-height: 1.5; font-weight: 400;">${agentDetails.description || 'No description'}</p>
                <div class="d-flex flex-wrap gap-2 mb-3">
                    <div class="bg-dark border border-secondary px-2 py-1 rounded small text-white opacity-50" style="font-size: 0.65rem; font-weight: 600;">
                        STYLE: ${agentDetails.agent_style || 'DEFAULT'}
                    </div>
                    <div class="bg-dark border border-secondary px-2 py-1 rounded small text-white opacity-50" style="font-size: 0.65rem; font-weight: 600;">
                        TOOLS: ${agentDetails.tools ? agentDetails.tools.length : 0}
                    </div>
                </div>
            </div>
        `;

        // Add tool details if available
        if (agentDetails.tool_details && agentDetails.tool_details.length > 0) {
            infoHtml += '<h6 class="mt-3">Tool Details:</h6><ul class="list-group list-group-flush">';
            agentDetails.tool_details.forEach(tool => {
                infoHtml += `
                <li class="list-group-item bg-transparent text-white border-top-0 border-end-0 border-start-0 border-secondary d-flex justify-content-between align-items-center">
                    <div>
                        <strong class="text-white-50">${tool.name}</strong>
                        <span class="text-secondary d-block">${tool.description || 'No description'}</span>
                    </div>
                    <div>
                        <span class="badge bg-transparent border ${tool.on_status === 'Online' ? 'border-white text-white' : 'border-secondary text-secondary'} rounded-0">
                            ${tool.on_status === 'Online' ? 'ON' : 'OFF'}
                        </span>
                    </div>
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

// Get agent info button handler
async function getAgentInfo() {
    const select = document.getElementById('agent-select');
    if (!select.value) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    // If we already have the agent details, just display them again
    if (currentAgentDetails) {
        let infoHtml = `
            <div class="card bg-transparent border-secondary text-white p-3 mb-3">
                <h5 class="fw-light border-bottom border-secondary pb-2 mb-2">${currentAgentDetails.agent_name}</h5>
                <p class="small text-secondary mb-2">${currentAgentDetails.description || 'No description'}</p>
                <div class="d-flex align-items-center gap-3 small">
                    <div><strong>Style:</strong> ${currentAgentDetails.agent_style || 'Default'}</div>
                    <div>
                        <strong>Status:</strong> 
                        <span class="badge bg-transparent border ${currentAgentDetails.on_status ? 'border-white text-white' : 'border-secondary text-secondary'} rounded-0">
                            ${currentAgentDetails.on_status ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                    </div>
                    <div><strong>Tools:</strong> ${currentAgentDetails.tools ? currentAgentDetails.tools.length : 0}</div>
                </div>
            </div>
        `;
        Utils.hideLoading('agent-info-container', infoHtml);
    } else {
        getAgentDetails(select.value);
    }
}

// Clear the chat container
function clearResponse() {
    document.getElementById('chat-container').innerHTML = '<div class="d-flex flex-column align-items-center justify-content-center h-100 opacity-50"><div class="icon-box bg-light text-muted mb-3 rounded-circle" style="width: 64px; height: 64px;"><i class="bi bi-chat-square-dots fs-3"></i></div><p class="text-muted">Select an agent and start the conversation.</p></div>';
    document.getElementById('tool-status-container').innerHTML = '';

    // Reset metrics
    document.getElementById('metric-model-init').textContent = '-';
    document.getElementById('metric-agent-init').textContent = '-';
    document.getElementById('metric-response-time').textContent = '-';
    document.getElementById('metric-recursion').textContent = '-';

    // document.getElementById('status-container').classList.add('d-none'); // Element removed in redesign
    // Reset the conversation history
    conversationHistory = [];
}

// Store conversation history
let conversationHistory = [];

// Invoke agent with streaming (Handles Text OR Image+Text)
async function invokeAgentStream() {
    const select = document.getElementById('agent-select');
    const agentId = select.value;

    if (!agentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    const messageInput = document.getElementById('agent-message');
    const message = messageInput.value.trim();

    // Require either a message OR an image
    if (!message && !selectedImage) {
        Utils.showNotification('Please enter a message or select an image', 'warning');
        return;
    }

    // Clear the input field
    messageInput.value = '';

    // If we don't have agent details, get them first
    if (!currentAgentDetails) {
        try {
            await getAgentDetails(agentId);
        } catch (error) {
            Utils.showNotification('Failed to get agent details. Please try again.', 'danger');
            return;
        }
    }

    // Close any existing EventSource
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }

    // Add user message to the chat (Pass image data if available)
    addMessageToChat('user', message, 'normal', selectedImage ? selectedImage.data : null);

    // Get thread_id (moved up so it can be used in payload construction)
    let threadId = document.getElementById('thread-id').value.trim();
    if (!threadId) {
        threadId = "1";
        document.getElementById('thread-id').value = threadId;
    }

    // Prepare the JSON payload structure
    const requestPayload = {
        input: {
            messages: message,  // Changed back to 'messages' to match AgentInputMessage schema
            image_path: selectedImage ? "temp_upload.jpg" : undefined, // Will be replaced by backend
            context: document.getElementById('agent-context').value
        },
        config: {
            configurable: {
                thread_id: threadId
            }
        },
        metadata: {
            model_name: document.getElementById('model-name').value || 'custom-vlm',
            reset_memory: document.getElementById('reset-memory').checked,
            load_from_json: document.getElementById('load-from-json').checked,
            agent_style: document.getElementById('agent-style').value
        },
        agent_config: currentAgentDetails
    };

    // --- Prepare Fetch Request ---
    const streamEndpoint = `/agent-invoke/${agentId}/invoke-stream`;
    const url = new URL(`${API.getBaseUrl()}${streamEndpoint}`);
    let fetchOptions = {
        method: 'POST',
        headers: {
            'Accept': 'text/event-stream',
            ...API.getHeaders(false) // Auth headers, false = no Content-Type (let browser set multipart)
        }
    };

    // --- ALWAYS USE MULTIPART/FORM-DATA ---
    // The backend endpoint expects 'data' as a Form field and 'image' as an optional File.
    // We must use FormData even for text-only requests to satisfy the backend signature.

    console.log(`Invoking agent for agent ID: ${agentId}`);

    const formData = new FormData();

    // Append the JSON structure as a string under the key 'data'
    formData.append('data', JSON.stringify(requestPayload));

    if (selectedImage) {
        // Convert the Base64 image data to a Blob and append it
        try {
            const fetchRes = await fetch(selectedImage.data);
            const blob = await fetchRes.blob();
            formData.append('image', blob, selectedImage.name || 'uploaded_image.png');
        } catch (e) {
            console.error("Error converting image to blob", e);
            Utils.showNotification("Error processing image upload", "danger");
            return;
        }

        // Clear selected image UI after sending
        removeSelectedImage();
    }

    fetchOptions.body = formData;
    // NOTE: Do NOT set 'Content-Type': 'application/json' or 'multipart/form-data'.
    // The browser automatically sets the correct Content-Type with boundary for FormData.

    try {
        // Update request details panel (Safeguarded)
        const reqUrlElem = document.getElementById('request-url');
        if (reqUrlElem) reqUrlElem.textContent = url.toString();

        const reqHeadersElem = document.getElementById('request-headers');
        if (reqHeadersElem) reqHeadersElem.textContent = JSON.stringify(fetchOptions.headers, null, 2);

        const reqBodyElem = document.getElementById('request-body');
        if (reqBodyElem) {
            if (selectedImage) {
                reqBodyElem.textContent = "[Multipart FormData with Image and JSON payload]";
            } else {
                reqBodyElem.textContent = JSON.stringify(requestPayload, null, 2);
            }
        }

        // Show status container (Safeguarded)
        const statusContainer = document.getElementById('status-container');
        if (statusContainer) statusContainer.classList.remove('d-none');

        document.getElementById('current-status').textContent = 'Connecting...';

        // Create agent message placeholder in the chat
        const agentMessageId = addMessageToChat('agent', '');
        const agentMessageElement = document.getElementById(agentMessageId);

        // Create a token container inside the agent message
        const tokenContainer = document.createElement('div');
        tokenContainer.className = 'token-container';
        tokenContainer.dataset.rawContent = '';
        agentMessageElement.appendChild(tokenContainer);

        // Reset buffering state for new message
        isBuffering = false;
        hasReceivedVlmResponse = false;
        visibleContent = '';
        bufferedContent = '';

        // Execute the fetch
        const response = await fetch(url, fetchOptions);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Get the response body as a ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Process the stream
        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                console.log('Stream complete');
                document.getElementById('current-status').textContent = 'Stream complete';

                // Add the final message to conversation history
                conversationHistory.push({
                    role: 'agent',
                    content: tokenContainer.dataset.rawContent
                });



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
                processEvent(eventData, tokenContainer);

                // Look for the next event
                eventEnd = buffer.indexOf('\n\n');
            }
        }

        // Add copy button to the final message
        // Add copy button to the final message
        if (!agentMessageElement.querySelector('.copy-button')) {
            const copyButton = document.createElement('button');
            // Clean, subtle icon-only button
            copyButton.className = 'btn btn-link btn-sm copy-button position-absolute top-0 end-0 m-2 p-0 text-decoration-none text-muted opacity-25';
            copyButton.style.transition = 'all 0.2s';

            // Hover effect
            copyButton.onmouseenter = () => { copyButton.classList.remove('opacity-25'); copyButton.classList.add('opacity-100'); };
            copyButton.onmouseleave = () => { copyButton.classList.remove('opacity-100'); copyButton.classList.add('opacity-25'); };

            copyButton.innerHTML = '<i class="bi bi-clipboard fs-6"></i>';
            copyButton.title = "Copy to clipboard";
            copyButton.onclick = () => {
                navigator.clipboard.writeText(tokenContainer.dataset.rawContent);
                copyButton.innerHTML = '<i class="bi bi-check-lg text-success fs-6"></i>';
                setTimeout(() => { copyButton.innerHTML = '<i class="bi bi-clipboard fs-6"></i>'; }, 2000);
            };
            agentMessageElement.appendChild(copyButton);
        }

        Utils.showNotification('Agent invocation complete', 'success');

    } catch (error) {
        // Add error message to the chat
        addMessageToChat('system', `Error: ${error.detail || error.message || 'Unknown error'}`, 'error');
        document.getElementById('current-status').textContent = 'Error';
        Utils.showNotification(`Error invoking agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Add a message to the chat (Updated to support images and custom IDs)
// Add a message to the chat (Updated to support images and custom IDs)
function addMessageToChat(role, content, type = 'normal', imageData = null, customId = null) {
    const chatContainer = document.getElementById('chat-container');

    // Remove the initial placeholder if it exists
    const placeholder = chatContainer.querySelector('p.text-center.text-muted') || chatContainer.querySelector('.d-flex.flex-column.align-items-center.justify-content-center');
    if (placeholder) {
        placeholder.remove();
    }

    // Create message element
    const messageElement = document.createElement('div');
    const messageId = customId || `message-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    messageElement.id = messageId;

    if (role === 'system') {
        // System messages (like errors)
        messageElement.className = 'alert alert-danger w-100 my-2';
        messageElement.innerHTML = content;
    } else {
        // User or agent messages - NEATER BUBBLE STYLE
        messageElement.className = `message-bubble ${role} chat-boundary mb-3`;

        // Create message content container
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        // Add image if present
        if (imageData) {
            const imgContainer = document.createElement('div');
            imgContainer.className = 'message-image mb-2';
            const img = document.createElement('img');
            img.src = imageData;
            img.alt = 'Uploaded content';
            img.className = 'img-fluid rounded';
            img.style.maxHeight = '200px';
            imgContainer.appendChild(img);
            messageContent.appendChild(imgContainer);
        }

        // Add text content if present
        if (content) {
            const textContent = document.createElement('div');
            textContent.textContent = content;
            messageContent.appendChild(textContent);
        }

        messageElement.appendChild(messageContent);

        // Add timestamp as a neat meta footer inside the bubble
        const meta = document.createElement('div');
        meta.className = 'message-meta mt-1 opacity-75 small';
        meta.style.fontSize = '0.7em';
        meta.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageElement.appendChild(meta);
    }

    // Add to conversation history if it's a user message
    if (role === 'user') {
        conversationHistory.push({
            role: 'user',
            content: content || '',
            image: imageData || undefined
        });
    }

    // Add to chat container
    chatContainer.appendChild(messageElement);

    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageId;
}

// Process an SSE event
function processEvent(eventData, tokenContainer) {
    // Split the event into lines
    const lines = eventData.split('\n');
    let eventType = '';
    let data = '';

    // Parse the event
    for (const line of lines) {
        if (line.startsWith('event:')) {
            eventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
            // Get data for SSE streaming - directly use the substring without any extra processing
            data = line.substring(5);
        }
    }

    // Skip if no event type or data
    if (!eventType || !data) {
        return;
    }

    try {
        // Parse the data as JSON
        const jsonData = JSON.parse(data);

        // Handle different event types
        switch (eventType) {
            case 'status':
                handleStatusEvent(jsonData);
                break;
            case 'tool_status':
                handleToolStatusEvent(jsonData);
                break;
            case 'token':
                if (hasReceivedVlmResponse) break;
                handleTokenEvent(jsonData, tokenContainer);
                break;
            case 'vlm_response':
                hasReceivedVlmResponse = true;
                // Display VLM caption as a system message or part of the agent's thought
                // For now, let's append it to the chat as a distinct block
                const vlmContent = `\n\n**VLM Analysis:** ${jsonData.caption}\n\n`;
                // We can append it to the token container directly so it appears before the agent's text
                tokenContainer.dataset.rawContent = (tokenContainer.dataset.rawContent || '') + vlmContent;
                tokenContainer.innerHTML = marked.parse(tokenContainer.dataset.rawContent);
                break;
            case 'metrics':
                handleMetricsEvent(jsonData);
                break;
            default:
                console.log(`Unknown event type: ${eventType}`, jsonData);
        }
    } catch (error) {
        console.error('Error processing event:', error, eventData);
    }
}

// Handle status events
function handleStatusEvent(data) {
    const statusContainer = document.getElementById('current-status');
    statusContainer.textContent = data.status;

    // If it's the final answer, add it to the response
    if (data.status === 'Agent Execution End' && data.final_answer) {
        // We don't need to do anything here since the tokens should have built up the answer
        console.log('Final answer received:', data.final_answer);
    }
}

// Handle tool status events
function handleToolStatusEvent(data) {
    const toolStatusContainer = document.getElementById('tool-status-container');
    if (!toolStatusContainer) return;

    // Create a new tool status element
    const toolStatusElement = document.createElement('div');
    toolStatusElement.className = `tool-log-entry mb-1 ${data.is_start ? 'text-info' : 'text-success'}`;

    // Format timestamp
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

    if (data.is_start) {
        // OPENING TAG
        let inputStr = '';
        if (data.input && Object.keys(data.input).length > 0) {
            inputStr = ` <span class="text-white ms-2">[INPUT: ${JSON.stringify(data.input).substring(0, 100)}${JSON.stringify(data.input).length > 100 ? '...' : ''}]</span>`;
        }
        toolStatusElement.innerHTML = `<span class="text-white me-2">[${time}]</span> <span class="fw-bold text-white">▶ EXECUTING:</span> <span class="text-white">${data.tool_name}</span>${inputStr}`;
    } else {
        // CLOSING TAG
        let outputStr = '';
        if (data.output) {
            let outText = typeof data.output === 'string' ? data.output : JSON.stringify(data.output);
            outputStr = ` <span class="text-white ms-2">[OUTPUT: ${outText.substring(0, 100)}${outText.length > 100 ? '...' : ''}]</span>`;
        }
        toolStatusElement.innerHTML = `<span class="text-white me-2">[${time}]</span> <span class="fw-bold text-white">✓ COMPLETED:</span> <span class="text-white">${data.tool_name}</span>${outputStr}`;
    }

    // Add to the container
    toolStatusContainer.appendChild(toolStatusElement);

    // Scroll to the bottom
    toolStatusContainer.scrollTop = toolStatusContainer.scrollHeight;
}

// Handle metrics events
function handleMetricsEvent(data) {
    const modelInitElem = document.getElementById('metric-model-init');
    const agentInitElem = document.getElementById('metric-agent-init');
    const responseTimeElem = document.getElementById('metric-response-time');
    const recursionElem = document.getElementById('metric-recursion');

    if (modelInitElem) modelInitElem.textContent = `${data.model_init_time.toFixed(4)}s`;
    if (agentInitElem) agentInitElem.textContent = `${data.agent_init_time.toFixed(4)}s`;
    if (responseTimeElem) responseTimeElem.textContent = `${data.response_time.toFixed(4)}s`;
    if (recursionElem) recursionElem.textContent = data.recursion_count;
}

// Global variables to track buffering state
let isBuffering = false;
let hasReceivedVlmResponse = false;
let visibleContent = '';
let bufferedContent = '';
let responseQueue = [];
let isTypingResponse = false;

// Handle token events
function handleTokenEvent(data, tokenContainer) {
    // Queue the token
    const token = data.token;
    responseQueue.push(token);

    // Start processing if not already active
    if (!isTypingResponse) {
        processResponseQueue(tokenContainer);
    }
}

// Process the response queue with typing effect
async function processResponseQueue(tokenContainer) {
    isTypingResponse = true;

    try {
        while (responseQueue.length > 0) {
            // Get the next chunk
            const chunk = responseQueue.shift();

            // Process character by character for typing effect
            for (const char of chunk) {
                // Check if container is still valid
                if (!tokenContainer.isConnected) {
                    responseQueue = []; // Clear queue if element gone
                    isTypingResponse = false;
                    return;
                }

                // Always concatenate the token to the raw content for processing
                tokenContainer.dataset.rawContent = (tokenContainer.dataset.rawContent || '') + char;

                // Process the content
                processContentWithBuffering(char, tokenContainer);

                // Scroll the chat container to the bottom
                const chatContainer = document.getElementById('chat-container');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }

                // Dynamic delay based on queue size (speed up if falling behind)
                // If queue has many chunks, go fast (0-5ms). heavy logic takes time anyway.
                // If clean queue, go nice speed (15-20ms).
                let delay = 15;
                if (responseQueue.length > 2) delay = 5;
                if (responseQueue.length > 10) delay = 0;

                if (delay > 0) {
                    await new Promise(r => setTimeout(r, delay));
                }
            }
        }
    } catch (error) {
        console.error('Error in typing loop:', error);
    } finally {
        isTypingResponse = false;

        // Safety check: if queue not empty (race condition), restart
        if (responseQueue.length > 0) {
            processResponseQueue(tokenContainer);
        }
    }
}

// Process content with buffering for special blocks
function processContentWithBuffering(token, tokenContainer) {
    // Add the token to the appropriate buffer
    if (isBuffering) {
        // We're in buffering mode, add to buffered content
        bufferedContent += token;

        // Check if we've reached the end marker
        if (bufferedContent.includes('!#/block#!')) {
            // We have a complete block, process it
            const blockEndIndex = bufferedContent.indexOf('!#/block#!') + '!#/block#!'.length;
            const completeBlock = bufferedContent.substring(0, blockEndIndex);
            const remainingBuffer = bufferedContent.substring(blockEndIndex);

            // Process the complete block
            const blockContent = completeBlock.substring('!#block#!'.length, completeBlock.length - '!#/block#!'.length);

            try {
                // Parse and render the special content
                const parsedContent = JSON.parse(blockContent);
                let renderedContent = '';

                // Render based on content type
                if (parsedContent.type && parsedContent.content) {
                    switch (parsedContent.type) {
                        case 'image':
                            renderedContent = renderImage(parsedContent.content);
                            break;
                        case 'video':
                            renderedContent = renderVideo(parsedContent.content);
                            break;
                        case 'markdown':
                            renderedContent = renderMarkdown(parsedContent.content);
                            break;
                        case 'html':
                            // For HTML content, we need to ensure scripts are executed
                            renderedContent = parsedContent.content;
                            // We'll use a setTimeout to ensure the HTML is inserted before executing scripts
                            setTimeout(() => {
                                // Find the parent message element that contains this HTML
                                const parentMessage = tokenContainer.closest('.message');
                                if (parentMessage) {
                                    // Execute any scripts in the HTML content
                                    executeScriptsInElement(parentMessage);
                                }
                            }, 0);
                            break;
                        case 'json':
                            renderedContent = renderJson(parsedContent.content);
                            break;
                        default:
                            renderedContent = `<div class="alert alert-warning">Unknown content type: ${parsedContent.type}</div>`;
                    }
                } else {
                    renderedContent = `<div class="alert alert-warning">Invalid content format: missing type or content</div>`;
                }

                // Add the rendered content to the visible content
                visibleContent += renderedContent;
            } catch (error) {
                console.error('Error processing special content:', error);
                visibleContent += `<div class="alert alert-danger">Error processing content: ${error.message}</div>`;
            }

            // Reset buffering state
            isBuffering = false;
            bufferedContent = remainingBuffer;

            // Check if there's more to buffer in the remaining content
            if (bufferedContent.includes('!#block#!')) {
                const parts = bufferedContent.split('!#block#!');
                visibleContent += parts[0];
                bufferedContent = '!#block#!' + parts.slice(1).join('!#block#!');
                isBuffering = true;
            } else {
                // No more blocks, add remaining buffer to visible content
                visibleContent += bufferedContent;
                bufferedContent = '';
            }
        } else {
            // We're in buffering mode but haven't found the end marker yet
            // Check if we've been buffering for too long without finding an end marker
            // This is a safety mechanism to prevent content from being hidden indefinitely
            if (bufferedContent.length > 2000) { // Arbitrary threshold
                // If we've buffered too much without finding the end marker,
                // assume this isn't actually a special block and show the content
                visibleContent += bufferedContent;
                bufferedContent = '';
                isBuffering = false;
            }
        }
    } else {
        // We're not in buffering mode, check if we need to start
        const newContent = visibleContent + token;

        if (newContent.includes('!#block#!')) {
            // Found start marker, enter buffering mode
            const parts = newContent.split('!#block#!');
            visibleContent = parts[0]; // Content before the marker
            bufferedContent = '!#block#!' + parts.slice(1).join('!#block#!'); // Content including and after the marker
            isBuffering = true;
        } else {
            // Regular content, just add to visible
            visibleContent = newContent;
        }
    }

    // Update the display with visible content
    tokenContainer.innerHTML = visibleContent;

    // Also update the parent message element if this is in a chat message
    const parentMessage = tokenContainer.closest('.message');
    if (parentMessage) {
        // Scroll chat container to bottom to follow the streaming text
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Render image content
function renderImage(content) {
    if (!content.src) {
        return '<div class="alert border-secondary text-white bg-transparent">Invalid image: missing src</div>';
    }

    const alt = content.alt || 'Image';
    const additionalInfo = content.additional ?
        `<div class="mt-1 small text-white-50">${JSON.stringify(content.additional)}</div>` : '';

    return `
        <div class="my-3 text-center">
            <img src="${content.src}" alt="${alt}" class="img-fluid border border-secondary" style="max-width: 100%;">
            <div class="mt-2 text-white-50 small">${alt}</div>
            ${additionalInfo}
        </div>
    `;
}

// Render video content
function renderVideo(content) {
    if (!content.src) {
        return '<div class="alert alert-warning">Invalid video: missing src</div>';
    }

    const alt = content.alt || 'Video';
    const additionalInfo = content.additional ?
        `<div class="mt-1 small text-muted">${JSON.stringify(content.additional)}</div>` : '';

    return `
        <div class="my-3 text-center">
            <video controls class="img-fluid" style="max-width: 100%;">
                <source src="${content.src}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <div class="mt-2 text-muted">${alt}</div>
            ${additionalInfo}
        </div>
    `;
}

// Render markdown content
function renderMarkdown(content) {
    try {
        // Use the marked library to render markdown
        return marked.parse(content);
    } catch (error) {
        console.error('Error rendering markdown:', error);
        return `<div class="alert alert-danger">Error rendering markdown: ${error.message}</div>`;
    }
}

// Render JSON content
function renderJson(content) {
    try {
        // Format JSON with syntax highlighting
        const formattedJson = JSON.stringify(content, null, 2);
        return `<pre class="bg-light p-3 rounded">${formattedJson}</pre>`;
    } catch (error) {
        console.error('Error rendering JSON:', error);
        return `<div class="alert alert-danger">Error rendering JSON: ${error.message}</div>`;
    }
}

// Execute scripts within an element
function executeScriptsInElement(element) {
    // Find all script elements
    const scripts = element.querySelectorAll('script');
    scripts.forEach(oldScript => {
        // Create a new script element
        const newScript = document.createElement('script');

        // Copy all attributes from the old script to the new one
        Array.from(oldScript.attributes).forEach(attr => {
            newScript.setAttribute(attr.name, attr.value);
        });

        // Copy the content of the script
        newScript.textContent = oldScript.textContent;

        // Replace the old script with the new one to trigger execution
        oldScript.parentNode.replaceChild(newScript, oldScript);
    });

    // Also handle onclick and other event attributes that might be in the HTML
    const elementsWithEvents = element.querySelectorAll('[onclick], [onchange], [onsubmit], [onmouseover], [onmouseout]');
    elementsWithEvents.forEach(el => {
        // Clone the element to re-attach event handlers
        const newEl = el.cloneNode(true);
        el.parentNode.replaceChild(newEl, el);
    });
}

