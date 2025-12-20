/**
 * Companies JavaScript file
 * Handles all company-related functionality
 */

// Global variables
let currentCompanyId = null;
let allRoles = [];

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!Utils.checkAuth()) return;
    
    // Add debug info
    console.log('JWT Token:', API.getToken());
    console.log('API URL:', API.getBaseUrl());
    console.log('Auth Headers:', API.getHeaders());
    
    // Load companies
    loadCompanies();
    
    // Load roles for the add user form
    loadRoles();
    
    // Event listeners
    document.getElementById('refresh-companies').addEventListener('click', loadCompanies);
    document.getElementById('save-company').addEventListener('click', saveCompany);
    document.getElementById('add-user-btn').addEventListener('click', showAddUserModal);
    document.getElementById('confirm-add-user').addEventListener('click', addUserToCompany);
    
    // Reset form when modal is opened for creating a new company
    document.getElementById('create-company-btn').addEventListener('click', function() {
        resetCompanyForm();
        document.getElementById('company-modal-label').textContent = 'Create Company';
    });
});

// Load all companies
async function loadCompanies() {
    try {
        Utils.showLoading('companies-container');
        
        console.log('Loading companies...');
        console.log('Headers:', API.getHeaders(false));
        
        const companies = await API.get('/companies');
        
        console.log('Companies loaded:', companies);
        
        if (companies.length === 0) {
            Utils.hideLoading('companies-container', '<p class="text-center">No companies found</p>');
            return;
        }
        
        let html = '<div class="row">';
        
        companies.forEach(company => {
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card company-card h-100">
                        <div class="card-body">
                            <h5 class="card-title">${company.name}</h5>
                            <p class="card-text">${company.description || 'No description'}</p>
                        </div>
                        <div class="card-footer">
                            <button class="btn btn-sm btn-primary view-company" data-id="${company.company_id}">View Users</button>
                            <button class="btn btn-sm btn-info edit-company" data-id="${company.company_id}">Edit</button>
                            <button class="btn btn-sm btn-danger delete-company" data-id="${company.company_id}">Delete</button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        Utils.hideLoading('companies-container', html);
        
        // Add event listeners to buttons
        document.querySelectorAll('.view-company').forEach(button => {
            button.addEventListener('click', function() {
                const companyId = this.getAttribute('data-id');
                loadCompanyUsers(companyId);
            });
        });
        
        document.querySelectorAll('.edit-company').forEach(button => {
            button.addEventListener('click', function() {
                const companyId = this.getAttribute('data-id');
                editCompany(companyId);
            });
        });
        
        document.querySelectorAll('.delete-company').forEach(button => {
            button.addEventListener('click', function() {
                const companyId = this.getAttribute('data-id');
                deleteCompany(companyId);
            });
        });
        
    } catch (error) {
        console.error('Error loading companies:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error loading companies';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.hideLoading('companies-container', `<p class="text-center text-danger">${errorMessage}</p>`);
        
        // Add a button to create a company if none exist
        Utils.hideLoading('companies-container', `
            <div class="text-center">
                <p class="text-danger">${errorMessage}</p>
                <p>You might not have any companies yet. Try creating one:</p>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#company-modal">Create Company</button>
            </div>
        `);
    }
}

// Load company users
async function loadCompanyUsers(companyId) {
    try {
        currentCompanyId = companyId;
        
        Utils.showLoading('company-users-container');
        
        console.log('Loading company users for company ID:', companyId);
        
        // Enable the add user button
        document.getElementById('add-user-btn').disabled = false;
        
        const users = await API.get(`/companies/${companyId}/users`);
        
        console.log('Company users loaded:', users);
        
        if (users.length === 0) {
            Utils.hideLoading('company-users-container', '<p class="text-center">No users found for this company</p>');
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-striped table-hover">';
        html += `
            <thead>
                <tr>
                    <th>User ID</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        users.forEach(user => {
            const roleName = getRoleName(user.role_id);
            
            html += `
                <tr>
                    <td>${user.user_id}</td>
                    <td>${roleName}</td>
                    <td>
                        <button class="btn btn-sm btn-danger remove-user" data-id="${user.user_id}">Remove</button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        
        Utils.hideLoading('company-users-container', html);
        
        // Add event listeners to remove user buttons
        document.querySelectorAll('.remove-user').forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.getAttribute('data-id');
                removeUserFromCompany(userId);
            });
        });
        
    } catch (error) {
        console.error('Error loading company users:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error loading company users';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.hideLoading('company-users-container', `<p class="text-center text-danger">${errorMessage}</p>`);
    }
}

// Get role name from role ID
function getRoleName(roleId) {
    const role = allRoles.find(r => r.role_id === roleId);
    return role ? role.role_name : 'Unknown Role';
}

// Load roles for the add user form
async function loadRoles() {
    try {
        console.log('Loading roles...');
        
        const roles = await API.get('/roles');
        
        console.log('Roles loaded:', roles);
        
        allRoles = roles;
        
        const roleSelect = document.getElementById('role-select');
        
        // Clear existing options
        roleSelect.innerHTML = '';
        
        // Add roles to select
        roles.forEach(role => {
            const option = new Option(role.role_name, role.role_id);
            roleSelect.add(option);
        });
        
    } catch (error) {
        console.error('Error loading roles:', error);
        console.error('Error details:', JSON.stringify(error));
    }
}

// Reset company form
function resetCompanyForm() {
    document.getElementById('company-form').reset();
    document.getElementById('company-id').value = '';
}

// Save company (create or update)
async function saveCompany() {
    try {
        const companyId = document.getElementById('company-id').value;
        const isUpdate = !!companyId;
        
        // Get form values
        const companyName = document.getElementById('company-name').value;
        const description = document.getElementById('company-description').value;
        
        // Create company data object
        const companyData = {
            name: companyName,
            description: description
        };
        
        console.log('Saving company:', companyData);
        console.log('Is update:', isUpdate);
        
        let response;
        
        if (isUpdate) {
            // Update existing company
            response = await API.put(`/companies/${companyId}`, companyData);
            Utils.showNotification('Company updated successfully');
        } else {
            // Create new company
            response = await API.post('/companies', companyData);
            Utils.showNotification('Company created successfully');
        }
        
        console.log('Company saved:', response);
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('company-modal'));
        modal.hide();
        
        // Reload companies
        loadCompanies();
        
    } catch (error) {
        console.error('Error saving company:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error saving company';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.showNotification(errorMessage, 'danger');
    }
}

// Edit company
async function editCompany(companyId) {
    try {
        console.log('Editing company with ID:', companyId);
        
        const company = await API.get(`/companies/${companyId}`);
        
        console.log('Company details loaded:', company);
        
        // Set form values
        document.getElementById('company-id').value = company.company_id;
        document.getElementById('company-name').value = company.name;
        document.getElementById('company-description').value = company.description || '';
        
        // Update modal title
        document.getElementById('company-modal-label').textContent = 'Edit Company';
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('company-modal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading company for editing:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error loading company for editing';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.showNotification(errorMessage, 'danger');
    }
}

// Delete company
async function deleteCompany(companyId) {
    if (!confirm('Are you sure you want to delete this company?')) {
        return;
    }
    
    try {
        console.log('Deleting company with ID:', companyId);
        
        await API.delete(`/companies/${companyId}`);
        
        console.log('Company deleted successfully');
        
        Utils.showNotification('Company deleted successfully');
        
        // Reload companies
        loadCompanies();
        
        // If we were viewing the company that was deleted, clear the users
        if (currentCompanyId === companyId) {
            currentCompanyId = null;
            document.getElementById('company-users-container').innerHTML = '<p class="text-center">Select a company to view users</p>';
            document.getElementById('add-user-btn').disabled = true;
        }
        
    } catch (error) {
        console.error('Error deleting company:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error deleting company';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.showNotification(errorMessage, 'danger');
    }
}

// Show add user modal
function showAddUserModal() {
    if (!currentCompanyId) {
        Utils.showNotification('Please select a company first', 'warning');
        return;
    }
    
    // Reset form
    document.getElementById('add-user-form').reset();
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('add-user-modal'));
    modal.show();
}

// Add user to company
async function addUserToCompany() {
    if (!currentCompanyId) {
        Utils.showNotification('Please select a company first', 'warning');
        return;
    }
    
    try {
        // Get form values
        const userId = document.getElementById('user-id').value;
        const roleId = document.getElementById('role-select').value;
        
        // Validate UUID format
        if (!isValidUUID(userId)) {
            Utils.showNotification('User ID must be a valid UUID (e.g., 9489c4d4-b30c-41df-a3d7-0062e2848343)', 'danger');
            return;
        }
        
        // Create user data object
        const userData = {
            user_id: userId,
            role_id: parseInt(roleId)
        };
        
        console.log('Adding user to company:', userData);
        console.log('Company ID:', currentCompanyId);
        
        // Add user to company
        await API.post(`/companies/${currentCompanyId}/users`, userData);
        
        console.log('User added to company successfully');
        
        Utils.showNotification('User added to company successfully');
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('add-user-modal'));
        modal.hide();
        
        // Reload company users
        loadCompanyUsers(currentCompanyId);
        
    } catch (error) {
        console.error('Error adding user to company:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error adding user to company';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.showNotification(errorMessage, 'danger');
    }
}

// Remove user from company
async function removeUserFromCompany(userId) {
    if (!currentCompanyId) {
        Utils.showNotification('Please select a company first', 'warning');
        return;
    }
    
    // Validate UUID format
    if (!isValidUUID(userId)) {
        Utils.showNotification('User ID must be a valid UUID', 'danger');
        return;
    }
    
    if (!confirm('Are you sure you want to remove this user from the company?')) {
        return;
    }
    
    try {
        console.log('Removing user from company:', userId);
        console.log('Company ID:', currentCompanyId);
        
        await API.delete(`/companies/${currentCompanyId}/users/${userId}`);
        
        console.log('User removed from company successfully');
        
        Utils.showNotification('User removed from company successfully');
        
        // Reload company users
        loadCompanyUsers(currentCompanyId);
        
    } catch (error) {
        console.error('Error removing user from company:', error);
        console.error('Error details:', JSON.stringify(error));
        
        let errorMessage = 'Error removing user from company';
        if (error.detail) {
            errorMessage += `: ${error.detail}`;
        } else if (error.message) {
            errorMessage += `: ${error.message}`;
        } else {
            errorMessage += ': Unknown error';
        }
        
        Utils.showNotification(errorMessage, 'danger');
    }
}

// Validate UUID format
function isValidUUID(uuid) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
}