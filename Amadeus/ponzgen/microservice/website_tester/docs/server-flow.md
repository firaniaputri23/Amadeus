# Website Tester Server Flow

## Overview

The Website Tester Server is a simple HTTP server module designed to serve the static files for the Website Tester application. It provides a lightweight, easy-to-use development server that makes the frontend components accessible via a web browser. The server is designed to automatically find an available port if the default port is already in use, making it flexible for development environments where multiple services may be running simultaneously.

## Application Components

1. **Server Script (`server.py`)**
   - A Python-based HTTP server implementation
   - Serves static HTML, CSS, JavaScript, and other assets
   - Handles port selection and availability checking
   - Provides colorized logging for better readability

2. **HTTP Request Handler**
   - Based on Python's `SimpleHTTPRequestHandler`
   - Customized for the Website Tester application
   - Handles incoming HTTP requests
   - Serves appropriate static files from the filesystem

## Server Flow

### 1. Server Initialization

1. The script is executed (typically via `python server.py`)
2. The working directory is set to the location of the script itself
3. The server attempts to start on the primary port (8008)
4. If the primary port is unavailable, it tries alternative ports in sequence (8009, 8010, 8011, 8012)
5. Once a port is successfully bound, the server starts listening for requests

### 2. Server Running State

1. The server displays a colorized confirmation message showing:
   - Server name
   - URL (http://localhost:port/)
   - Instructions to stop the server (Ctrl+C)
2. The server enters its main loop, waiting for incoming connections
3. When requests arrive, they are handled by the custom request handler
4. Each request is logged to the console with timestamp and request details

### 3. Request Handling

1. When a browser makes a request to the server:
   - If requesting the root URL ("/"), the server returns index.html
   - For other paths, the server looks for matching files in the filesystem
   - Static files (HTML, CSS, JS, images) are served directly
2. Each response is logged to the console with colorized output
3. The server continues handling requests until stopped

### 4. Server Termination

1. When the user presses Ctrl+C, a KeyboardInterrupt is triggered
2. The server catches this exception and begins shutdown procedures
3. The server socket is closed properly
4. A colorized shutdown message is displayed
5. The script exits

## Port Selection Process

1. The server first attempts to use the primary port (8008)
2. If port 8008 is in use, it tries each alternative port in sequence:
   - 8009
   - 8010
   - 8011
   - 8012
3. If all ports are in use, an error message is displayed
4. For each port attempt:
   - The server tries to bind to the port
   - If successful, it starts serving on that port
   - If an "Address already in use" error occurs, it tries the next port

## Configuration Options

The server has the following configurable settings (defined as constants):

1. **PRIMARY_PORT**
   - Default: 8008
   - The first port the server attempts to use

2. **ALTERNATIVE_PORTS**
   - Default: [8009, 8010, 8011, 8012]
   - Fallback ports to try if the primary port is unavailable

## Request Handler Customization

The custom `MyHTTPRequestHandler` class extends the standard Python `SimpleHTTPRequestHandler` with:

1. **Custom Logging**
   - Colorized output (green text)
   - Timestamp and request details
   - Makes server messages easier to spot in terminal output

2. **Headers Handling**
   - Uses standard HTTP headers
   - No additional CORS headers are added
   - Maintains the default behavior of SimpleHTTPRequestHandler

## File Serving Process

The server serves files according to these rules:

1. Files are served relative to the script's directory
2. When a request is received, the path is mapped to the local filesystem
3. If the file exists, it's served with the appropriate MIME type
4. If the file doesn't exist, a 404 error is returned
5. Directory requests (ending with /) serve the index.html file in that directory

## Data Requirements

The Website Tester Server has minimal data requirements:

1. **Static Files**
   - HTML files (e.g., index.html, agents.html, roles.html)
   - JavaScript files (in js/ directory)
   - CSS files (in css/ directory)
   - Any other assets (images, fonts, etc.)

2. **Runtime Environment**
   - Python 3.x
   - Standard library modules:
     - http.server
     - socketserver
     - os
     - sys
     - socket

## Deployment Considerations

1. **Development Use Only**
   - This server is intended for development and testing purposes
   - Not recommended for production environments
   - Lacks security features needed for public deployment

2. **Port Availability**
   - Requires one of the specified ports to be available
   - Will fail if all configured ports are in use
   - May require adjusting firewall settings to allow incoming connections

3. **Network Access**
   - By default, the server binds to all interfaces (0.0.0.0)
   - Can be accessed from other machines on the same network
   - Use http://localhost:port/ for local access

## Integration with Frontend Applications

The server's primary purpose is to serve the Website Tester frontend application:

1. **HTML Files**
   - Main pages for the application (e.g., index.html, roles.html)
   - Provides the user interface

2. **JavaScript Files**
   - Frontend logic located in js/ directory
   - Handles API calls to backend services
   - Manages user interaction and data display

3. **CSS Files**
   - Styling for the application interface
   - Located in css/ directory

## Running the Server

To run the server:

1. Navigate to the website_tester directory
2. Execute `python server.py`
3. The server will start on port 8008 (or an alternative port if 8008 is unavailable)
4. Access the application at http://localhost:8008/ (or whichever port is being used)
5. Press Ctrl+C in the terminal to stop the server

## Troubleshooting

Common issues and solutions:

1. **All Ports In Use**
   - Error message: "All ports are in use. Please free up one of these ports: [8008, 8009, 8010, 8011, 8012]"
   - Solution: Stop other services using these ports or modify the port list in the script

2. **Permission Errors**
   - Error: Unable to bind to port (permission denied)
   - Solution: Run the script with appropriate permissions or use ports above 1024

3. **File Not Found Errors**
   - Browser shows 404 errors
   - Solution: Ensure the requested files exist in the correct directory structure 