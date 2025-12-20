/**
 * User Info JavaScript file
 * Handles user information functionality
 */

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!Utils.checkAuth()) return;
    
    // Load user info
    loadUserInfo();
    
    // Parse and display JWT token info
    displayTokenInfo();
    
    // Event listeners
    document.getElementById('refresh-user-info').addEventListener('click', loadUserInfo);
});

// Load user information
async function loadUserInfo() {
    try {
        Utils.showLoading('user-info-container');
        
        const userInfo = await API.get('/user/info');
        
        let html = '<div class="row">';
        html += '<div class="col-md-12">';
        
        // User profile section
        html += `
            <div class="card mb-4">
                <div class="card-body">
                    <h4 class="card-title">User Profile</h4>
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>User ID:</strong> ${userInfo.id || userInfo.user_id || 'Not available'}</p>
                            <p><strong>Email:</strong> ${userInfo.email || 'Not available'}</p>
                            <p><strong>Name:</strong> ${userInfo.name || userInfo.user_name || 'Not available'}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Created:</strong> ${userInfo.created_at ? Utils.formatDate(userInfo.created_at) : 'Not available'}</p>
                            <p><strong>Last Sign In:</strong> ${userInfo.last_sign_in_at ? Utils.formatDate(userInfo.last_sign_in_at) : 'Not available'}</p>
                            <p><strong>Role:</strong> ${userInfo.role || 'Not available'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add JSON representation
        html += `
            <div class="card">
                <div class="card-body">
                    <h4 class="card-title">JSON Representation</h4>
                    <div class="json-display">
                        ${JSON.stringify(userInfo, null, 2)}
                    </div>
                </div>
            </div>
        `;
        
        html += '</div>';
        html += '</div>';
        
        Utils.hideLoading('user-info-container', html);
        
    } catch (error) {
        Utils.hideLoading('user-info-container', `
            <div class="alert alert-danger">
                <h4 class="alert-heading">Error loading user information</h4>
                <p>${error.detail || error.message || 'Unknown error'}</p>
                <hr>
                <p class="mb-0">Please check your JWT token and try again.</p>
            </div>
        `);
    }
}

// Parse and display JWT token information
function displayTokenInfo() {
    const token = API.getToken();
    
    if (!token) {
        document.getElementById('token-info-container').innerHTML = `
            <div class="alert alert-warning">
                <h4 class="alert-heading">No JWT Token</h4>
                <p>No JWT token is set. Please set a token on the home page.</p>
            </div>
        `;
        return;
    }
    
    try {
        // Parse JWT token (without verification)
        const parts = token.split('.');
        if (parts.length !== 3) {
            throw new Error('Invalid JWT token format');
        }
        
        // Decode header and payload
        const header = JSON.parse(atob(parts[0]));
        const payload = JSON.parse(atob(parts[1]));
        
        let html = '<div class="row">';
        
        // Header section
        html += `
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-body">
                        <h4 class="card-title">Token Header</h4>
                        <div class="json-display">
                            ${JSON.stringify(header, null, 2)}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Payload section
        html += `
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-body">
                        <h4 class="card-title">Token Payload</h4>
                        <div class="json-display">
                            ${JSON.stringify(payload, null, 2)}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Token expiration info
        let expirationInfo = 'No expiration information available';
        if (payload.exp) {
            const expirationDate = new Date(payload.exp * 1000);
            const now = new Date();
            const isExpired = expirationDate < now;
            
            expirationInfo = `
                <div class="alert ${isExpired ? 'alert-danger' : 'alert-info'}">
                    <h4 class="alert-heading">${isExpired ? 'Token Expired' : 'Token Expiration'}</h4>
                    <p>Expiration Date: ${expirationDate.toLocaleString()}</p>
                    ${isExpired ? 
                        '<p class="mb-0">Your token has expired. Please get a new token.</p>' : 
                        `<p class="mb-0">Your token is valid for ${Math.floor((expirationDate - now) / (1000 * 60 * 60))} hours and ${Math.floor(((expirationDate - now) % (1000 * 60 * 60)) / (1000 * 60))} minutes.</p>`
                    }
                </div>
            `;
        }
        
        // Add expiration info
        html += `
            <div class="col-md-12">
                ${expirationInfo}
            </div>
        `;
        
        html += '</div>';
        
        document.getElementById('token-info-container').innerHTML = html;
        
    } catch (error) {
        document.getElementById('token-info-container').innerHTML = `
            <div class="alert alert-danger">
                <h4 class="alert-heading">Error Parsing JWT Token</h4>
                <p>${error.message}</p>
                <hr>
                <p class="mb-0">Please check that your token is in the correct format.</p>
            </div>
        `;
    }
}

// Helper function to decode base64 URL safely
function atob(str) {
    // Convert base64url to base64
    const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
    // Pad with '=' if needed
    const pad = base64.length % 4;
    const padded = pad === 0 ? base64 : base64 + '='.repeat(4 - pad);
    
    try {
        return window.atob(padded);
    } catch (e) {
        throw new Error('Invalid base64 string');
    }
}