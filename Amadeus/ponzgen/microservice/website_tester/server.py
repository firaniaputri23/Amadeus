#!/usr/bin/env python3
"""
Simple HTTP server for the website tester
Serves static files on port 8008 or alternative ports if 8008 is in use
"""

import http.server
import socketserver
import os
import sys
import socket

# Set the primary port and alternatives
PRIMARY_PORT = 8008
ALTERNATIVE_PORTS = [8009, 8010, 8011, 8012]

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Override to set headers that disable CORS restrictions
    def end_headers(self):
        # No CORS headers as requested
        http.server.SimpleHTTPRequestHandler.end_headers(self)
    
    def log_message(self, format, *args):
        # Print colored log messages
        sys.stderr.write("\033[92m[%s] %s\033[0m\n" % (self.log_date_time_string(), format % args))

def run_server():
    # Change to the directory of the script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Try to start the server on the primary port, then fall back to alternatives
    ports_to_try = [PRIMARY_PORT] + ALTERNATIVE_PORTS
    
    for port in ports_to_try:
        try:
            # Create the server
            handler = MyHTTPRequestHandler
            httpd = socketserver.TCPServer(("", port), handler)
            
            print(f"\n\033[1;32m=== Website Tester Server ===\033[0m")
            print(f"\033[1;32m→ Server running at http://localhost:{port}/\033[0m")
            print(f"\033[1;32m→ Press Ctrl+C to stop the server\033[0m\n")
            
            try:
                # Start the server
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\033[1;33m→ Server stopped by user\033[0m")
                httpd.server_close()
                return
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"\033[1;31m→ Port {port} is already in use, trying next port...\033[0m")
                continue
            else:
                raise
    
    print("\033[1;31m→ All ports are in use. Please free up one of these ports: {ports_to_try}\033[0m")

if __name__ == "__main__":
    run_server()
