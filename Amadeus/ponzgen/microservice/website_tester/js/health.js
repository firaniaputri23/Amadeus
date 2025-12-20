/**
 * Health Check JavaScript file
 * Handles API health check functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Event listeners
    document.getElementById('api-url-select').addEventListener('change', toggleCustomUrlField);
    document.getElementById('check-health').addEventListener('click', checkHealth);
    
    // Initialize
    toggleCustomUrlField();
});

// Toggle custom URL field based on selection
function toggleCustomUrlField() {
    const urlSelect = document.getElementById('api-url-select');
    const customUrlContainer = document.getElementById('custom-url-container');
    
    if (urlSelect.value === 'custom') {
        customUrlContainer.style.display = 'block';
    } else {
        customUrlContainer.style.display = 'none';
    }
}

// Get the appropriate API URL based on selection
function getSelectedApiUrl() {
    const urlSelect = document.getElementById('api-url-select');
    
    switch (urlSelect.value) {
        case 'regular':
            return localStorage.getItem('api_url') || 'http://localhost:8000';
        case 'invoke':
            return localStorage.getItem('invoke_api_url') || 'http://localhost:8001';
        case 'custom':
            return document.getElementById('custom-url').value;
        default:
            return 'http://localhost:8000';
    }
}

// Check API health
async function checkHealth() {
    const endpoint = document.getElementById('endpoint').value.trim();
    const includeAuth = document.getElementById('include-auth').checked;
    
    const apiUrl = getSelectedApiUrl();
    const fullUrl = `${apiUrl}${endpoint}`;
    
    // Update request details
    document.getElementById('request-url').textContent = fullUrl;
    
    // Prepare headers
    let headers = {};
    if (includeAuth) {
        const token = localStorage.getItem('jwt_token');
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    document.getElementById('request-headers').textContent = JSON.stringify(headers, null, 2);
    
    // Show loading
    document.getElementById('response-container').innerHTML = '<p>Loading...</p>';
    
    try {
        // Make the request
        const requestOptions = {
            method: 'GET',
            headers: headers
        };
        
        console.log('Request options:', requestOptions);
        
        const response = await fetch(fullUrl, requestOptions);
        
        let responseHtml = '';
        
        // Add status information
        responseHtml += `<p><strong>Status:</strong> ${response.status} ${response.statusText}</p>`;
        responseHtml += '<p><strong>Response Headers:</strong></p>';
        
        // Add response headers
        const responseHeaders = {};
        response.headers.forEach((value, key) => {
            responseHeaders[key] = value;
        });
        responseHtml += `<pre>${JSON.stringify(responseHeaders, null, 2)}</pre>`;
        
        // Add response body
        responseHtml += '<p><strong>Response Body:</strong></p>';
        
        try {
            const data = await response.json();
            responseHtml += `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        } catch (e) {
            // If not JSON, try to get text
            try {
                const text = await response.text();
                responseHtml += `<pre>${text}</pre>`;
            } catch (e2) {
                responseHtml += '<p>Could not parse response body</p>';
            }
        }
        
        document.getElementById('response-container').innerHTML = responseHtml;
        
    } catch (error) {
        console.error('Health check error:', error);
        
        let errorHtml = '<div class="alert alert-danger">';
        errorHtml += `<p><strong>Error:</strong> ${error.message}</p>`;
        
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            errorHtml += '<p>This could be due to:</p>';
            errorHtml += '<ul>';
            errorHtml += '<li>Server not running or unreachable</li>';
            errorHtml += '<li>Network connectivity issues</li>';
            errorHtml += '</ul>';
        }
        
        errorHtml += '</div>';
        
        document.getElementById('response-container').innerHTML = errorHtml;
    }
}
