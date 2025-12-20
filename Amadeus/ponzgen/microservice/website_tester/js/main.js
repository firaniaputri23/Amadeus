/**
 * Main JavaScript file for API Tester
 * Contains utility functions for API requests and authentication
 */

// API request utility functions
if (typeof API === 'undefined') {
    API = {
        // JWT Secret from .env - should match the server's JWT_SECRET
        JWT_SECRET: "XNz40SzR7jx+33ScALVyBbpNugroBT+LL1VFaywzXwIEygfZFNJtoHD/cSk+GuRz9KAmltO5ENMu9XVYsvE+6g==",

        // Get the base URL from localStorage
        getBaseUrl: function () {
            const storedUrl = localStorage.getItem('api_url');
            const url = storedUrl || 'http://localhost:8080';
            const trimmedUrl = url.trim();

            // Auto-fix if there's a space issue
            if (storedUrl && storedUrl !== trimmedUrl) {
                console.warn('Fixed API URL with spaces:', storedUrl, '→', trimmedUrl);
                localStorage.setItem('api_url', trimmedUrl);
            }

            return trimmedUrl;
        },

        // For backward compatibility, returns the same URL as getBaseUrl
        getInvokeUrl: function () {
            return this.getBaseUrl();
        },

        // Parse JWT token
        parseJwt: function (token) {
            try {
                const base64Url = token.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                return JSON.parse(atob(base64));
            } catch (e) {
                return null;
            }
        },

        // Validate JWT token format and expiration
        validateToken: function (token) {
            if (!token) return false;

            try {
                // Check if token has the correct format (header.payload.signature)
                const parts = token.split('.');
                if (parts.length !== 3) return false;

                // Parse the token to check expiration
                const payload = this.parseJwt(token);
                if (!payload) return false;

                // Check if token is expired
                const currentTime = Math.floor(Date.now() / 1000);
                if (payload.exp && payload.exp < currentTime) {
                    console.error('Token has expired');
                    return false;
                }

                // In a production environment, you would also verify the signature here
                // For security, this should be done on the server side
                // The actual signature verification would require the JWT secret and a JWT library

                return true; // Token is valid

            } catch (error) {
                console.error('Token validation error:', error);
                return false;
            }
        },

        // Get the JWT token from localStorage and validate it
        getToken: function () {
            const token = localStorage.getItem('jwt_token');
            if (!this.validateToken(token)) {
                console.error('Invalid or expired token');
                localStorage.removeItem('jwt_token');
                return null;
            }
            return token;
        },

        // Check if authentication is set up
        isAuthenticated: function () {
            return !!this.getToken();
        },

        // Headers for authenticated requests
        getHeaders: function (contentType = true) {
            console.log('getToken:', this.getToken());
            const headers = {
                'Authorization': `Bearer ${this.getToken()}`
            };

            if (contentType) {
                headers['Content-Type'] = 'application/json';
            }

            return headers;
        },

        // GET request
        get: async function (endpoint) {
            try {
                console.log(`GET request to ${this.getBaseUrl()}${endpoint}`);
                console.log('Headers:', this.getHeaders(false));

                const response = await fetch(`${this.getBaseUrl()}${endpoint}`, {
                    method: 'GET',
                    headers: this.getHeaders(false)
                });

                console.log(`Response status: ${response.status}`);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({
                        detail: `HTTP error! Status: ${response.status}`
                    }));
                    console.error('Response error:', errorData);
                    throw errorData;
                }

                const data = await response.json();
                console.log('Response data:', data);
                return data;
            } catch (error) {
                console.error('GET Error:', error);
                throw error;
            }
        },

        // POST request
        post: async function (endpoint, data) {
            try {
                console.log(`POST request to ${this.getBaseUrl()}${endpoint}`);
                console.log('Headers:', this.getHeaders());
                console.log('Request data:', data);

                const response = await fetch(`${this.getBaseUrl()}${endpoint}`, {
                    method: 'POST',
                    headers: this.getHeaders(),
                    body: JSON.stringify(data)
                });

                console.log(`Response status: ${response.status}`);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({
                        detail: `HTTP error! Status: ${response.status}`
                    }));
                    console.error('Response error:', errorData);
                    throw errorData;
                }

                const responseData = await response.json();
                console.log('Response data:', responseData);
                return responseData;
            } catch (error) {
                console.error('POST Error:', error);
                throw error;
            }
        },

        // PUT request
        put: async function (endpoint, data) {
            try {
                console.log(`PUT request to ${this.getBaseUrl()}${endpoint}`);
                console.log('Headers:', this.getHeaders());
                console.log('Request data:', data);

                const response = await fetch(`${this.getBaseUrl()}${endpoint}`, {
                    method: 'PUT',
                    headers: this.getHeaders(),
                    body: JSON.stringify(data)
                });

                console.log(`Response status: ${response.status}`);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({
                        detail: `HTTP error! Status: ${response.status}`
                    }));
                    console.error('Response error:', errorData);
                    throw errorData;
                }

                const responseData = await response.json();
                console.log('Response data:', responseData);
                return responseData;
            } catch (error) {
                console.error('PUT Error:', error);
                throw error;
            }
        },

        // DELETE request
        delete: async function (endpoint) {
            try {
                console.log(`DELETE request to ${this.getBaseUrl()}${endpoint}`);
                console.log('Headers:', this.getHeaders(false));

                const response = await fetch(`${this.getBaseUrl()}${endpoint}`, {
                    method: 'DELETE',
                    headers: this.getHeaders(false)
                });

                console.log(`Response status: ${response.status}`);

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({
                        detail: `HTTP error! Status: ${response.status}`
                    }));
                    console.error('Response error:', errorData);
                    throw errorData;
                }

                // Some DELETE endpoints might not return JSON
                try {
                    const responseData = await response.json();
                    console.log('Response data:', responseData);
                    return responseData;
                } catch (e) {
                    // If the response is not JSON, return a success message
                    return { message: "Operation completed successfully" };
                }
            } catch (error) {
                console.error('DELETE Error:', error);
                throw error;
            }
        }
    };
}

// Utility functions
if (typeof Utils === 'undefined') {
    Utils = {
        // Format date
        formatDate: function (dateString) {
            const date = new Date(dateString);
            return date.toLocaleString();
        },

        // Create a notification
        showNotification: function (message, type = 'success') {
            const container = document.getElementById('notification-container');

            if (!container) {
                // Create container if it doesn't exist
                const newContainer = document.createElement('div');
                newContainer.id = 'notification-container';
                newContainer.style.position = 'fixed';
                newContainer.style.top = '20px';
                newContainer.style.right = '20px';
                newContainer.style.zIndex = '1000';
                document.body.appendChild(newContainer);
            }

            const notification = document.createElement('div');
            notification.className = `alert alert-${type} alert-dismissible fade show`;
            notification.role = 'alert';
            notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

            document.getElementById('notification-container').appendChild(notification);

            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => {
                    notification.remove();
                }, 150);
            }, 5000);
        },

        // Check authentication and redirect if not authenticated
        checkAuth: function () {
            if (!API.isAuthenticated()) {
                Utils.showNotification('Please set your JWT token in the home page', 'danger');
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 2000);
                return false;
            }
            return true;
        },

        // Create a loading spinner
        showLoading: function (elementId) {
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
            }
        },

        // Hide loading spinner and set content
        hideLoading: function (elementId, content) {
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = content;
            }
        },

        // Create a table from data
        createTable: function (data, columns) {
            if (!data || data.length === 0) {
                return '<p>No data available</p>';
            }

            let tableHtml = '<div class="table-responsive"><table class="table table-striped table-hover">';

            // Table header
            tableHtml += '<thead><tr>';
            columns.forEach(column => {
                tableHtml += `<th>${column.header}</th>`;
            });
            tableHtml += '<th>Actions</th></tr></thead>';

            // Table body
            tableHtml += '<tbody>';
            data.forEach(item => {
                tableHtml += '<tr>';
                columns.forEach(column => {
                    let value = item[column.field];

                    // Format value if needed
                    if (column.format) {
                        value = column.format(value, item);
                    }

                    tableHtml += `<td>${value}</td>`;
                });

                // Actions column
                tableHtml += '<td>';
                if (item.actions) {
                    item.actions.forEach(action => {
                        tableHtml += `<button class="${action.class}" data-id="${item.id}" data-action="${action.name}">${action.label}</button> `;
                    });
                }
                tableHtml += '</td>';

                tableHtml += '</tr>';
            });
            tableHtml += '</tbody></table></div>';

            return tableHtml;
        }
    };
}

// Check authentication on page load (except for index.html)
document.addEventListener('DOMContentLoaded', function () {
    if (window.location.pathname.indexOf('index.html') === -1) {
        Utils.checkAuth();
    }
});