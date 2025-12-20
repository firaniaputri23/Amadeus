import subprocess
import socket
import time
import json
import threading
import os
import logging
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class MCPProxyManager:
    def __init__(self):
        self._processes = {}  # Store processes by port
        self._commands = {}   # Store full commands by port

    def start(self, arr_full_cmd):
        """Start all MCP proxy processes from a list of full commands."""
        for cmd in arr_full_cmd:
            port = self._extract_port(cmd)
            if port:
                try:
                    # Set environment variables to ensure proper PATH
                    env = os.environ.copy()
                    
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                              text=True, bufsize=1, env=env)
                    self._processes[port] = process
                    self._commands[port] = cmd
                    logger.info(f"Started: {cmd}")
                    
                    # Start a thread to read output
                    output_thread = threading.Thread(target=self._read_process_output, args=(process, port))
                    output_thread.daemon = True
                    output_thread.start()
                except Exception as e:
                    logger.error(f"Error starting process on port {port}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())

    def check_status(self):
        """Check if processes are running based on ports."""
        for port in self._processes.keys():
            if self._is_port_in_use(port):
                print(f"✅ Running on port {port}")
            else:
                print(f"❌ NOT running on port {port}")

    def stop_all(self):
        """Stop all running processes."""
        for port, process in self._processes.items():
            process.terminate()
            print(f"Stopped process on port {port}")
        self._processes.clear()
        self._commands.clear()
        
    def stop_process(self, port):
        """Stop a specific process by port."""
        if port in self._processes:
            self._processes[port].terminate()
            print(f"Stopped process on port {port}")
            del self._processes[port]
            if port in self._commands:
                del self._commands[port]
            return True
        return False
        
    def update_tools(self, tools_data: List[Dict[str, Any]]):
        """
        Update running tools based on the provided tools data.
        
        Args:
            tools_data: List of tool dictionaries from the database
        
        Returns:
            Dict with information about the update process
        """
        result = {
            "added": [],
            "removed": [],
            "unchanged": [],
            "updated": []
        }
        
        # Extract full commands from tools data
        new_commands = {}
        for tool in tools_data:
            if "full_cmd" in tool and tool["full_cmd"]:
                port = self._extract_port(tool["full_cmd"])
                if port:
                    new_commands[port] = tool["full_cmd"]
        
        # Find commands to remove (in current but not in new)
        ports_to_remove = set(self._commands.keys()) - set(new_commands.keys())
        for port in ports_to_remove:
            cmd = self._commands[port]
            self.stop_process(port)
            result["removed"].append({"port": port, "cmd": cmd})
        
        # Check for commands to add or update
        for port, cmd in new_commands.items():
            if port not in self._commands:
                # New command to add
                try:
                    # Set environment variables to ensure proper PATH
                    env = os.environ.copy()
                    
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                              text=True, bufsize=1, env=env)
                    self._processes[port] = process
                    self._commands[port] = cmd
                    result["added"].append({"port": port, "cmd": cmd})
                    print(f"Started: {cmd}")
                    
                    # Start a thread to read output
                    # output_thread = threading.Thread(target=self._read_process_output, args=(process, port))
                    # output_thread.daemon = True
                    # output_thread.start()
                except Exception as e:
                    print(f"Error starting process on port {port}: {str(e)}")
                    result["added"].append({"port": port, "cmd": cmd, "error": str(e)})
                    import traceback
                    traceback.print_exc()
            elif self._commands[port] != cmd:
                # Command changed, restart
                self.stop_process(port)
                try:
                    # Set environment variables to ensure proper PATH
                    env = os.environ.copy()
                    
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                              text=True, bufsize=1, env=env)
                    self._processes[port] = process
                    self._commands[port] = cmd
                    result["updated"].append({"port": port, "cmd": cmd})
                    print(f"Updated: {cmd}")
                    
                    # Start a thread to read output
                    # output_thread = threading.Thread(target=self._read_process_output, args=(process, port))
                    # output_thread.daemon = True
                    # output_thread.start()
                except Exception as e:
                    print(f"Error updating process on port {port}: {str(e)}")
                    result["updated"].append({"port": port, "cmd": cmd, "error": str(e)})
                    import traceback
                    traceback.print_exc()
            else:
                # Command unchanged
                result["unchanged"].append({"port": port, "cmd": cmd})
                
        return result

    def _extract_port(self, cmd):
        """Extract the port number from the command string."""
        parts = cmd.split()
        if "--sse-port=" in cmd:
            for part in parts:
                if part.startswith("--sse-port="):
                    return int(part.split("=")[1])
        return None  # Return None if no port found

    def _is_port_in_use(self, port):
        """Check if a given port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0
            
    def _read_process_output(self, process, port):
        """Read and handle output from a process in a separate thread."""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(f"[{timestamp}][Port {port}] {line.strip()}")
        except Exception as e:
            logger.error(f"Error reading output from process on port {port}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

# Example usage
if __name__ == "__main__":
    arr_full_cmd = [
        "mcp-proxy --sse-port=10021 -e test333 test123 -- uvx mcp-server-fetch",
        "mcp-proxy --sse-port=10022 -e env1 value1 -e env2 value2 -- uvx mcp-server-fetch"
    ]

    manager = MCPProxyManager()
    manager.start(arr_full_cmd)

    time.sleep(3)  # Give processes time to start
    manager.check_status()

    # time.sleep(5)  # Wait before stopping
    # manager.stop_all()