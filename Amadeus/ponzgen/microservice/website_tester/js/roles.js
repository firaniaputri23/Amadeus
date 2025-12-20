/**
 * Roles JavaScript file
 * Handles all role-related functionality
 */

// Global variables
let currentRoleId = null;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!Utils.checkAuth()) return;
    
    // Load roles
    loadRoles();
    
    // Event listeners
    document.getElementById('refresh-roles').addEventListener('click', loadRoles);
});

// Load all roles
async function loadRoles() {
    try {
        Utils.showLoading('roles-container');
        
        const roles = await API.get('/roles');
        
        if (roles.length === 0) {
            Utils.hideLoading('roles-container', '<p class="text-center">No roles found</p>');
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-striped table-hover">';
        html += `
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Description</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        roles.forEach(role => {
            html += `
                <tr>
                    <td>${role.role_id}</td>
                    <td>${role.role_name}</td>
                    <td>${role.description || 'No description'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-role" data-id="${role.role_id}">View</button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        
        Utils.hideLoading('roles-container', html);
        
        // Add event listeners to view buttons
        document.querySelectorAll('.view-role').forEach(button => {
            button.addEventListener('click', function() {
                const roleId = this.getAttribute('data-id');
                loadRoleDetails(roleId);
            });
        });
        
    } catch (error) {
        Utils.hideLoading('roles-container', `<p class="text-center text-danger">Error loading roles: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}

// Load role details
async function loadRoleDetails(roleId) {
    try {
        currentRoleId = roleId;
        
        Utils.showLoading('role-details-container');
        
        const role = await API.get(`/roles/${roleId}`);
        
        let detailsHtml = `
            <h4>${role.role_name}</h4>
            <p>${role.description || 'No description'}</p>
            <p><strong>Role ID:</strong> ${role.role_id}</p>
        `;
        
        // Add permissions section if available
        if (role.permissions) {
            detailsHtml += `
                <h5 class="mt-4">Permissions</h5>
                <ul class="list-group">
            `;
            
            for (const [key, value] of Object.entries(role.permissions)) {
                detailsHtml += `
                    <li class="list-group-item">
                        <strong>${key}:</strong> ${value ? 'Yes' : 'No'}
                    </li>
                `;
            }
            
            detailsHtml += '</ul>';
        }
        
        // Add JSON representation
        detailsHtml += `
            <h5 class="mt-4">JSON Representation</h5>
            <div class="json-display">
                ${JSON.stringify(role, null, 2)}
            </div>
        `;
        
        Utils.hideLoading('role-details-container', detailsHtml);
        
    } catch (error) {
        Utils.hideLoading('role-details-container', `<p class="text-center text-danger">Error loading role details: ${error.detail || error.message || 'Unknown error'}</p>`);
    }
}