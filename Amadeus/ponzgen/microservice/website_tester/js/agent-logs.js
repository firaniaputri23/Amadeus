/**
 * Agent Logs JavaScript file
 * Handles all agent log-related functionality
 */

// Global variables
let currentLogId = null;
let allAgents = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!Utils.checkAuth()) return;
    
    // Load agents for select dropdowns
    loadAgents();
    
    // Event listeners
    document.getElementById('log-form').addEventListener('submit', function(e) {
        e.preventDefault();
        createAgentLog();
    });
    
    document.getElementById('refresh-logs').addEventListener('click', function() {
        const agentId = document.getElementById('agent-filter').value;
        if (agentId) {
            loadAgentLogs(agentId);
        } else {
            Utils.showNotification('Please select an agent first', 'warning');
        }
    });
    
    document.getElementById('agent-filter').addEventListener('change', function() {
        const agentId = this.value;
        if (agentId) {
            loadAgentLogs(agentId);
        } else {
            document.getElementById('logs-container').innerHTML = '<p class="text-center">Select an agent to view logs</p>';
        }
    });
});

// Load all agents
async function loadAgents() {
    try {
        const agents = await API.get('/agents');
        allAgents = agents;
        
        const agentSelect = document.getElementById('agent-select');
        const agentFilter = document.getElementById('agent-filter');
        
        // Clear existing options (except the first one)
        while (agentSelect.options.length > 1) {
            agentSelect.remove(1);
        }
        
        while (agentFilter.options.length > 1) {
            agentFilter.remove(1);
        }
        
        // Add agents to selects
        agents.forEach(agent => {
            const selectOption = new Option(agent.agent_name, agent.agent_id);
            const filterOption = new Option(agent.agent_name, agent.agent_id);
            
            agentSelect.add(selectOption);
            agentFilter.add(filterOption);
        });
        
    } catch (error) {
        console.error('Error loading agents:', error);
        Utils.showNotification(`Error loading agents: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Load agent logs
async function loadAgentLogs(agentId) {
    try {
        Utils.showLoading('logs-container');
        
        const logs = await API.get(`/agent-logs/agent/${agentId}`);
        
        if (logs.length === 0) {
            Utils.hideLoading('logs-container', '<p class="text-center">No logs found for this agent</p>');
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-striped table-hover">';
        html += `
            <thead>
                <tr>
                    <th>Log ID</th>
                    <th>Date</th>
                    <th>Input Tokens</th>
                    <th>Output Tokens</th>
                    <th>Embedding Tokens</th>
                    <th>Pricing</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        logs.forEach(log => {
            html += `
                <tr>
                    <td>${log.agent_log_id}</td>
                    <td>${Utils.formatDate(log.date)}</td>
                    <td>${log.input_token}</td>
                    <td>${log.output_token}</td>
                    <td>${log.embedding_token}</td>
                    <td>$${log.pricing}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-log" data-id="${log.agent_id}">View</button>
                        <button class="btn btn-sm btn-danger delete-log" data-id="${log.agent_id}">Delete</button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        
        Utils.hideLoading('logs-container', html);
        
        // Add event listeners to buttons
        document.querySelectorAll('.view-log').forEach(button => {
            button.addEventListener('click', function() {
                const logId = this.getAttribute('data-id');
                loadLogDetails(logId);
            });
        });
        
        document.querySelectorAll('.delete-log').forEach(button => {
            button.addEventListener('click', function() {
                const logId = this.getAttribute('data-id');
                deleteLog(logId);
            });
        });
        
    } catch (error) {
        Utils.hideLoading('logs-container', `<p class="text-center text-danger">Error loading logs: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}

// Load log details
async function loadLogDetails(agentId) {
    try {
        currentLogId = agentId;
        
        Utils.showLoading('log-details-container');
        
        const log = await API.get(`/agent-logs/${agentId}`);
        
        // Find agent name
        const agent = allAgents.find(a => a.agent_id === log.agent_id);
        const agentName = agent ? agent.agent_name : 'Unknown Agent';
        
        let detailsHtml = `
            <h4>Latest Log for Agent: ${agentName}</h4>
            <p><strong>Agent ID:</strong> ${log.agent_id}</p>
            <p><strong>Date:</strong> ${Utils.formatDate(log.date)}</p>
            
            <div class="row">
                <div class="col-md-6">
                    <h5>Token Information</h5>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Input Tokens
                            <span class="badge bg-primary rounded-pill">${log.input_token}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Output Tokens
                            <span class="badge bg-primary rounded-pill">${log.output_token}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Embedding Tokens
                            <span class="badge bg-primary rounded-pill">${log.embedding_token}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Total Tokens
                            <span class="badge bg-primary rounded-pill">${log.input_token + log.output_token + log.embedding_token}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Pricing
                            <span class="badge bg-success rounded-pill">$${log.pricing}</span>
                        </li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h5>Model Information</h5>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Model Protocol
                            <span>${log.model_protocol || 'Not specified'}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Temperature
                            <span>${log.model_temperature || 'Not specified'}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Media Input
                            <span class="badge ${log.media_input ? 'bg-success' : 'bg-secondary'}">${log.media_input ? 'Yes' : 'No'}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Media Output
                            <span class="badge ${log.media_output ? 'bg-success' : 'bg-secondary'}">${log.media_output ? 'Yes' : 'No'}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Use Memory
                            <span class="badge ${log.use_memory ? 'bg-success' : 'bg-secondary'}">${log.use_memory ? 'Yes' : 'No'}</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            Use Tool
                            <span class="badge ${log.use_tool ? 'bg-success' : 'bg-secondary'}">${log.use_tool ? 'Yes' : 'No'}</span>
                        </li>
                    </ul>
                </div>
            </div>
            <h5>Chat History</h5>
        `;
        
        // Check if chat history exists and has threads
        if (log.chat_history && log.chat_history.length > 0) {
            // Extract thread IDs from chat history
            const threadIds = new Set();
            let hasThreadStructure = false;
            
            // Check if the chat history has the new thread structure
            if (log.chat_history[0] && log.chat_history[0].thread_id !== undefined) {
                // Old format with thread_id in each message
                log.chat_history.forEach(message => {
                    if (message.thread_id) {
                        threadIds.add(message.thread_id);
                    }
                });
            } else if (log.chat_history[0] && log.chat_history[0].messages !== undefined) {
                // New format with thread objects
                hasThreadStructure = true;
                log.chat_history.forEach(thread => {
                    if (thread.thread_id) {
                        threadIds.add(thread.thread_id);
                    }
                });
            }
            
            // Add thread ID dropdown if we have threads
            if (threadIds.size > 0) {
                detailsHtml += `
                    <div class="mb-3">
                        <label for="thread-id-select" class="form-label">Select Thread ID</label>
                        <select class="form-select" id="thread-id-select">
                `;
                
                // Add "All Threads" option
                detailsHtml += `<option value="all">All Threads</option>`;
                
                // Add thread ID options
                Array.from(threadIds).forEach(threadId => {
                    detailsHtml += `<option value="${threadId}">${threadId}</option>`;
                });
                
                detailsHtml += `
                        </select>
                    </div>
                `;
            }
            
            // Add chat history container
            detailsHtml += '<div id="chat-messages-container" class="chat-history mb-3"></div>';
            
        } else {
            detailsHtml += '<p>No chat history available</p>';
        }
        
        // Add JSON representation
        detailsHtml += `
            <h5>JSON Representation</h5>
            <div class="json-display">
                ${JSON.stringify(log, null, 2)}
            </div>
        `;
        
        Utils.hideLoading('log-details-container', detailsHtml);
        
        // Now that the HTML is rendered, set up the thread display functionality
        if (log.chat_history && log.chat_history.length > 0) {
            const threadSelect = document.getElementById('thread-id-select');
            if (threadSelect) {
                // Function to display messages based on thread ID
                function displayMessages(threadId) {
                    const container = document.getElementById('chat-messages-container');
                    if (!container) return;
                    
                    container.innerHTML = '';
                    
                    const hasThreadStructure = log.chat_history[0] && log.chat_history[0].messages !== undefined;
                    
                    if (hasThreadStructure) {
                        // New format with thread objects
                        log.chat_history.forEach(thread => {
                            if (threadId === 'all' || thread.thread_id === threadId) {
                                // Add thread header
                                container.innerHTML += `<div class="thread-header mb-2"><strong>Thread ID: ${thread.thread_id}</strong></div>`;
                                
                                // Add messages
                                if (thread.messages && thread.messages.length > 0) {
                                    thread.messages.forEach(message => {
                                        const isUser = message.role === 'user';
                                        container.innerHTML += `
                                            <div class="chat-message ${isUser ? 'user-message' : 'assistant-message'}">
                                                <div class="message-header">
                                                    <strong>${isUser ? 'User' : 'Assistant'}</strong>
                                                </div>
                                                <div class="message-content">
                                                    ${message.content}
                                                </div>
                                            </div>
                                        `;
                                    });
                                } else {
                                    container.innerHTML += '<p>No messages in this thread</p>';
                                }
                                
                                // Add separator between threads
                                if (threadId === 'all') {
                                    container.innerHTML += '<hr class="my-3">';
                                }
                            }
                        });
                    } else {
                        // Old format with thread_id in each message
                        const filteredMessages = threadId === 'all'
                            ? log.chat_history
                            : log.chat_history.filter(message => message.thread_id === threadId);
                        
                        if (filteredMessages.length > 0) {
                            filteredMessages.forEach(message => {
                                const isUser = message.role === 'user';
                                container.innerHTML += `
                                    <div class="chat-message ${isUser ? 'user-message' : 'assistant-message'}">
                                        <div class="message-header">
                                            <strong>${isUser ? 'User' : 'Assistant'}</strong>
                                            ${message.thread_id ? `<span class="badge bg-secondary ms-2">Thread: ${message.thread_id}</span>` : ''}
                                        </div>
                                        <div class="message-content">
                                            ${message.content}
                                        </div>
                                    </div>
                                `;
                            });
                        } else {
                            container.innerHTML = '<p>No messages in this thread</p>';
                        }
                    }
                }
                
                // Add event listener for thread ID dropdown
                threadSelect.addEventListener('change', function() {
                    displayMessages(this.value);
                });
                
                // Initial display of all threads
                displayMessages('all');
            }
        }
        
    } catch (error) {
        Utils.hideLoading('log-details-container', `<p class="text-center text-danger">Error loading log details: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}

// Create agent log
async function createAgentLog() {
    try {
        // Get form values
        const agentId = document.getElementById('agent-select').value;
        const inputToken = parseInt(document.getElementById('input-token').value);
        const outputToken = parseInt(document.getElementById('output-token').value);
        const embeddingToken = parseInt(document.getElementById('embedding-token').value);
        const pricing = parseFloat(document.getElementById('pricing').value);
        const modelProtocol = document.getElementById('model-protocol').value;
        const modelTemperature = parseFloat(document.getElementById('model-temperature').value);
        const mediaInput = document.getElementById('media-input').checked;
        const mediaOutput = document.getElementById('media-output').checked;
        const useMemory = document.getElementById('use-memory').checked;
        const useTool = document.getElementById('use-tool').checked;
        
        // Parse chat history
        let chatHistory;
        try {
            chatHistory = JSON.parse(document.getElementById('chat-history').value);
        } catch (e) {
            Utils.showNotification('Invalid JSON in chat history', 'danger');
            return;
        }
        
        // Create log data object
        const logData = {
            agent_id: agentId,
            input_token: inputToken,
            output_token: outputToken,
            embedding_token: embeddingToken,
            pricing: pricing,
            chat_history: chatHistory,
            model_protocol: modelProtocol,
            model_temperature: modelTemperature,
            media_input: mediaInput,
            media_output: mediaOutput,
            use_memory: useMemory,
            use_tool: useTool
        };
        
        // Create log
        const response = await API.post('/agent-logs', logData);
        Utils.showNotification('Agent log created successfully');
        
        // Reset form
        document.getElementById('log-form').reset();
        document.getElementById('chat-history').value = '[\n    {"role": "user", "content": "What\'s the weather like today?"},\n    {"role": "assistant", "content": "It\'s sunny with a high of 75°F."}\n]';
        
        // If we have the agent filter set to this agent, reload the logs
        const agentFilter = document.getElementById('agent-filter');
        if (agentFilter.value === agentId) {
            loadAgentLogs(agentId);
        }
        
    } catch (error) {
        Utils.showNotification(`Error creating log: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Delete log
async function deleteLog(agentId) {
    if (!confirm('Are you sure you want to delete all logs for this agent?')) {
        return;
    }
    
    try {
        await API.delete(`/agent-logs/${agentId}`);
        Utils.showNotification('All logs for this agent deleted successfully');
        
        // Reload logs for the current agent
        const agentId = document.getElementById('agent-filter').value;
        if (agentId) {
            loadAgentLogs(agentId);
        }
        
        // If we were viewing logs for the agent that was deleted, clear the details
        if (currentLogId === agentId) {
            currentLogId = null;
            document.getElementById('log-details-container').innerHTML = '<p class="text-center">Select a log to view details</p>';
        }
        
    } catch (error) {
        Utils.showNotification(`Error deleting log: ${error.detail || error.message || 'Unknown error'}`, 'danger');
    }
}

// Add some CSS for chat messages
document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        .chat-history {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .chat-message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }
        
        .user-message {
            background-color: #f1f8ff;
            margin-right: 20%;
        }
        
        .assistant-message {
            background-color: #f8f9fa;
            margin-left: 20%;
        }
        
        .message-header {
            margin-bottom: 5px;
            color: #495057;
        }
        
        .message-content {
            white-space: pre-wrap;
        }
    `;
    document.head.appendChild(style);
});