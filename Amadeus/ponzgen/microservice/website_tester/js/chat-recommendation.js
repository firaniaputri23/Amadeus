/**
 * Agent Invoke Stream JavaScript file
 * Handles agent invocation with streaming responses
 */

// Current agent details stored globally
let currentAgentDetails = null;
let eventSource = null;

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
    document.getElementById('invoke-agent').addEventListener('click', invokeAgentStream);
    document.getElementById('clear-response').addEventListener('click', clearResponse);

    // Add event listener for Enter key in the message input
    document.getElementById('agent-message').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            invokeAgentStream();
        }
    });
});

// Load available LLM models from the API
async function loadAvailableModels() {
    try {
        const modelSelect = document.getElementById('model-name');
        modelSelect.innerHTML = '<option value="">Loading models...</option>';

        console.log('Loading available LLM models...');

        // Fetch available models from the API
        const response = await API.get('/get-llms');

        if (response && response.available_models && response.available_models.length > 0) {
            // Clear the select and add the models
            modelSelect.innerHTML = '';

            response.available_models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });

            console.log(`Loaded ${response.available_models.length} models`);
        } else {
            // If no models returned, add some defaults
            modelSelect.innerHTML = `
                <option value="custom-vlm">custom-vlm</option>
            `;
            console.log('No models returned from API, using defaults');
        }
    } catch (error) {
        console.error('Error loading models:', error);
        // Set default models in case of error
        document.getElementById('model-name').innerHTML = `
            <option value="custom-vlm">custom-vlm</option>
        `;
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

// Clear the chat container
function clearResponse() {
    // Clear chat messages
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.innerHTML = '<p class="text-center text-muted">Start a conversation with the agent</p>';
    }

    // Clear tool status
    const toolStatusContainer = document.getElementById('tool-status-container');
    if (toolStatusContainer) {
        toolStatusContainer.innerHTML = '';
    }

    // Hide status container
    const statusContainer = document.getElementById('status-container');
    if (statusContainer) {
        statusContainer.classList.add('d-none');
    }

    // Reset conversation history
    conversationHistory = [];
}

// Store conversation history
let conversationHistory = [];

// Invoke agent with streaming
async function invokeAgentStream() {
    const select = document.getElementById('agent-select');
    const agentId = select.value;

    if (!agentId) {
        Utils.showNotification('Please select an agent first', 'warning');
        return;
    }

    const messageInput = document.getElementById('agent-message');
    const message = messageInput.value.trim();

    if (!message) {
        Utils.showNotification('Please enter a message', 'warning');
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

    // Add user message to the chat
    addMessageToChat('user', message);

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
        const streamEndpoint = `/agent-invoke/${agentId}/invoke-stream`;
        document.getElementById('request-url').textContent = `${API.getBaseUrl()}${streamEndpoint}`;
        document.getElementById('request-headers').textContent = JSON.stringify({
            ...API.getHeaders(),
            'Accept': 'text/event-stream'
        }, null, 2);
        document.getElementById('request-body').textContent = JSON.stringify(requestBody, null, 2);

        // Show status container
        document.getElementById('status-container').classList.remove('d-none');
        document.getElementById('current-status').textContent = 'Connecting...';

        // Create agent message in the chat
        const agentMessageId = addMessageToChat('agent', '');
        const agentMessageElement = document.getElementById(agentMessageId);

        // Create a token container inside the agent message
        const tokenContainer = document.createElement('div');
        tokenContainer.className = 'token-container';
        tokenContainer.dataset.rawContent = '';
        agentMessageElement.appendChild(tokenContainer);

        // Reset buffering state for new message
        isBuffering = false;
        visibleContent = '';
        bufferedContent = '';

        console.log(`Invoking agent with streaming for agent ID: ${agentId}`);
        console.log('Request body:', requestBody);

        // Create URL with query parameters for the POST body
        const url = new URL(`${API.getBaseUrl()}${streamEndpoint}`);

        // Create headers with authorization
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            ...API.getHeaders()
        };

        // Use fetch to make a POST request with the EventSource
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(requestBody)
        });

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

        // Process chat recommendations after agent response
        try {
            // Wait for the agent response to complete and get the final message
            const finalMessage = await new Promise((resolve) => {
                const interval = setInterval(() => {
                    const messages = document.querySelectorAll('.message');
                    if (messages.length > 0) {
                        clearInterval(interval);
                        resolve(messages[messages.length - 1].textContent);
                    }
                }, 100);
            });

            // Send recommendations request with the complete conversation
            const recommendationsResponse = await fetch(`${API.getBaseUrl()}/chat-recommendation/generate-recommendations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${API.getToken()}`
                },
                body: JSON.stringify({
                    agent_id: agentId,
                    messages: [
                        {
                            role: 'user',
                            content: message
                        },
                        {
                            role: 'assistant',
                            content: finalMessage
                        }
                    ],
                    user_input: message,
                    conversation_id: null
                })
            });

            if (!recommendationsResponse.ok) {
                if (recommendationsResponse.status === 404) {
                    console.warn('Chat recommendation endpoint not found (404). Feature may be disabled.');
                    return;
                }
                throw new Error(`Failed to get recommendations: ${recommendationsResponse.status}`);
            }

            const response = await recommendationsResponse.json();
            const recommendationsContainer = document.getElementById('recommendations-container');

            // Clear existing recommendations
            recommendationsContainer.innerHTML = '';

            // Add new recommendations
            if (response && response.recommendations && Array.isArray(response.recommendations) && response.recommendations.length > 0) {
                response.recommendations.forEach(rec => {
                    const recElement = document.createElement('div');
                    recElement.className = 'recommendation-item alert alert-info mb-2 recommendation-bubble';
                    recElement.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="mb-1 recommendation-text">${rec.text || rec}</span>
                            <button class="btn btn-sm btn-primary btn-apply" onclick="applyRecommendation('${(rec.text || rec).replace(/'/g, "\\'")}', ${rec.confidence || 0.8})">Apply</button>
                        </div>
                    `;
                    recommendationsContainer.appendChild(recElement);
                });

                // Show recommendations container
                recommendationsContainer.style.display = 'block';
                Utils.showNotification('Agent invocation complete with recommendations', 'success');
            } else {
                console.log('No recommendations returned or invalid format:', response);
                recommendationsContainer.style.display = 'none';
            }

            // Show recommendations container
            recommendationsContainer.style.display = 'block';

            Utils.showNotification('Agent invocation complete with recommendations', 'success');

        } catch (recError) {
            console.error('Error processing recommendations:', recError);
            Utils.showNotification('Error getting recommendations', 'warning');
        }

    } catch (error) {
        // Add error message to the chat
        addMessageToChat('system', `Error: ${error.detail || error.message || 'Unknown error'}`, 'error');
        document.getElementById('current-status').textContent = 'Error';
        Utils.showNotification(`Error invoking agent: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Add a message to the chat
function addMessageToChat(role, content, type = 'normal') {
    const chatContainer = document.getElementById('chat-container');

    // Remove the initial placeholder if it exists
    const placeholder = chatContainer.querySelector('p.text-center.text-muted');
    if (placeholder) {
        chatContainer.removeChild(placeholder);
    }

    // Create message element
    const messageElement = document.createElement('div');
    const messageId = `message-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    messageElement.id = messageId;

    if (role === 'system') {
        // System messages (like errors)
        messageElement.className = 'alert alert-danger w-100 my-2';
        messageElement.innerHTML = content;
    } else {
        // User or agent messages
        messageElement.className = `message ${role}-message`;
        messageElement.innerHTML = content;

        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'message-time';
        timestamp.textContent = new Date().toLocaleTimeString();
        messageElement.appendChild(timestamp);

        // Add to conversation history if it's a user message
        if (role === 'user') {
            conversationHistory.push({
                role: 'user',
                content: content
            });
        }
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
                handleTokenEvent(jsonData, tokenContainer);
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
    try {
        // Get the tool status container
        const toolStatusContainer = document.getElementById('tool-status-container');
        if (!toolStatusContainer) {
            console.error('Tool status container not found');
            return;
        }

        // Create a new tool status element
        const toolStatusElement = document.createElement('div');
        toolStatusElement.className = `tool-status ${data.is_start ? 'start' : 'end'}`;

        // Create the content
        let content = '';
        if (data.tool_name) {
            content += `<strong>${data.tool_name}</strong>: ${data.status || ''}`;
        }

        // Add input or output if available
        if (data.input) {
            try {
                const inputStr = JSON.stringify(data.input);
                content += `<br><small>Input: ${inputStr}</small>`;
            } catch (e) {
                console.error('Error stringifying input:', e);
            }
        }

        if (data.output) {
            try {
                const outputStr = JSON.stringify(data.output);
                content += `<br><small>Output: ${outputStr}</small>`;
            } catch (e) {
                console.error('Error stringifying output:', e);
            }
        }

        toolStatusElement.innerHTML = content;

        // Add to the container
        toolStatusContainer.appendChild(toolStatusElement);

        // Scroll to the bottom
        toolStatusContainer.scrollTop = toolStatusContainer.scrollHeight;
    } catch (error) {
        console.error('Error in handleToolStatusEvent:', error);
    }
}

// Global variables to track buffering state
let isBuffering = false;
let visibleContent = '';
let bufferedContent = '';

/**
 * Apply a recommendation to the chat
 * @param {string} recommendationJson - JSON string of the recommendation object
 */
function applyRecommendation(text, confidence) {
    try {
        const messageInput = document.getElementById('agent-message');

        // Clear existing message
        messageInput.value = '';

        // Add the recommendation text to the message input
        messageInput.value = text;

        // Store the confidence in a data attribute
        messageInput.setAttribute('data-confidence', confidence);

        // Automatically send the message
        invokeAgentStream();
    } catch (error) {
        console.error('Error applying recommendation:', error);
        alert('Failed to apply recommendation. Please try again.');
    }
}

// Handle token events
function handleTokenEvent(data, tokenContainer) {
    // Get the raw token directly from the data
    const token = data.token;

    // Always concatenate the token to the raw content for processing
    tokenContainer.dataset.rawContent += token;

    // Process the content with buffering logic
    processContentWithBuffering(token, tokenContainer);

    // Scroll the chat container to the bottom
    const chatContainer = document.getElementById('chat-container');
    chatContainer.scrollTop = chatContainer.scrollHeight;
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

// Parse and render special content based on type
function parseAndRenderSpecialContent(tokenContainer) {
    let content = tokenContainer.dataset.rawContent;
    let result = '';

    // Process all special blocks in the content
    while (content.includes('!#block#!') && content.includes('!#/block#!')) {
        // Find the start and end of the block
        const blockStartIndex = content.indexOf('!#block#!');
        const blockEndIndex = content.indexOf('!#/block#!') + '!#/block#!'.length;

        // Get the text before the block
        const textBeforeBlock = content.substring(0, blockStartIndex);

        // Get the block content
        const blockContent = content.substring(
            blockStartIndex + '!#block#!'.length,
            blockEndIndex - '!#/block#!'.length
        ).trim();

        // Get the text after the block
        const textAfterBlock = content.substring(blockEndIndex);

        // Add the text before the block to the result
        result += textBeforeBlock;

        try {
            // Parse the JSON content
            const parsedContent = JSON.parse(blockContent);

            // Render based on content type
            if (parsedContent.type && parsedContent.content) {
                switch (parsedContent.type) {
                    case 'image':
                        result += renderImage(parsedContent.content);
                        break;
                    case 'video':
                        result += renderVideo(parsedContent.content);
                        break;
                    case 'markdown':
                        result += renderMarkdown(parsedContent.content);
                        break;
                    case 'html':
                        result += parsedContent.content; // Directly insert HTML
                        break;
                    case 'json':
                        result += renderJson(parsedContent.content);
                        break;
                    default:
                        result += `<div class="alert alert-warning">Unknown content type: ${parsedContent.type}</div>`;
                }
            } else {
                result += `<div class="alert alert-warning">Invalid content format: missing type or content</div>`;
            }
        } catch (error) {
            console.error('Error parsing special content:', error);
            result += `<div class="alert alert-danger">Error parsing content: ${error.message}</div>`;
            result += `<pre>${blockContent}</pre>`;
        }

        // Update content to process any remaining blocks
        content = textAfterBlock;
    }

    // Add any remaining content
    result += content;

    // Update the display
    tokenContainer.innerHTML = result;
}

// Render image content
function renderImage(content) {
    if (!content.src) {
        return '<div class="alert alert-warning">Invalid image: missing src</div>';
    }

    const alt = content.alt || 'Image';
    const additionalInfo = content.additional ?
        `<div class="mt-1 small text-muted">${JSON.stringify(content.additional)}</div>` : '';

    return `
        <div class="my-3 text-center">
            <img src="${content.src}" alt="${alt}" class="img-fluid" style="max-width: 100%;">
            <div class="mt-2 text-muted">${alt}</div>
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