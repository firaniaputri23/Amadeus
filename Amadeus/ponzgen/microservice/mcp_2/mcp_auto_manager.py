#!/usr/bin/env python3
"""
MCP Auto Manager

Unified MCP management system that:
- Fetches tools from Supabase
- Monitors for database changes
- Auto-restarts when commands change
- Health checks with configurable intervals
- Clean process management
"""

import os
import socket
import subprocess
import signal
import sys
import time
import threading
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

try:
    import schedule
except ImportError:
    print("Installing required package: schedule")
    subprocess.check_call(["pip", "install", "schedule"])
    import schedule


class MCPAutoManager:
    def __init__(self):
        load_dotenv()
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.check_interval = int(os.getenv("MCP_CHECK_INTERVAL_MINUTES", "10"))
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Use a fixed directory path from environment variable
        runner_dir_env = os.getenv("MCP_RUNNER_DIR")
        if runner_dir_env:
            self.runner_dir = Path(runner_dir_env)
            print(f"✅ Using runner directory from environment: {self.runner_dir}")
        else:
            # Use a fixed directory in the microservice/mcp_2 folder
            self.runner_dir = Path(os.path.join(os.getcwd(), "microservice", "mcp_2", "runner_files"))
            print(f"✅ Using fixed runner directory: {self.runner_dir}")
            
        # Ensure directory has proper permissions
        os.makedirs(self.runner_dir, exist_ok=True)
        try:
            os.chmod(self.runner_dir, 0o777)
        except Exception as e:
            print(f"⚠️ Warning: Could not set permissions on runner directory: {e}")
        self.envs_dir = self.runner_dir / "envs"
        self.logs_dir = self.runner_dir / "logs"
        self.state_file = self.runner_dir / "manager_state.json"
        
        self.running_processes = {}
        self.current_tools_hash = None
        self.current_tools_signatures = {}  # Track individual tool signatures
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.runner_dir.mkdir(exist_ok=True)
        self.envs_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get online, offline, and inactive MCP tools from Supabase."""
        try:
            response = self.supabase.table("tools_with_decrypted_keys").select("*").not_.in_("on_status", ["Offline", "Predefined"]).execute()
            print("response", response)
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Error fetching tools from Supabase: {e}")
            return []
    
    def _parse_mcp_tools(self, tools_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse tools data into command format."""
        parsed_tools = []
        
        for tool in tools_data:
            if not tool.get('versions'):
                continue
                
            latest_version = tool['versions'][-1]
            if not latest_version.get('released'):
                continue
                
            released = latest_version['released']
            print(released)
            tool_name = tool.get('name', 'unknown')
            
            # Build command
            port = released.get('port', '10000')
            print(port)
            args = released.get('args', '')
            env_vars = released.get('env', {})
            env_flags = " ".join([f"-e {key} {value}" for key, value in env_vars.items()])
            command = f"mcp-proxy --sse-port={port} {env_flags} -- {args}".strip()
            print(command)
            
            parsed_tools.append({
                'name': tool_name,
                'command': command,
                'port': port
            })
        
        return parsed_tools
    
    def _calculate_tools_hash(self, tools: List[Dict[str, Any]]) -> str:
        """Calculate hash of tools configuration for change detection."""
        tools_str = json.dumps(tools, sort_keys=True)
        return hashlib.md5(tools_str.encode()).hexdigest()
    
    def _get_tool_signature(self, tool: Dict[str, Any]) -> str:
        """Get unique signature for a single tool."""
        tool_data = {
            'name': tool['name'],
            'command': tool['command'],
            'port': tool['port']
        }
        return hashlib.md5(json.dumps(tool_data, sort_keys=True).encode()).hexdigest()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load manager state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading state: {e}")
        return {}
    
    def _save_state(self, state: Dict[str, Any]):
        """Save manager state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving state: {e}")
    
    def _kill_existing_mcp_processes(self):
        """Kill all existing mcp-proxy processes."""
        try:
            print("🧹 Cleaning up existing mcp-proxy processes...")
            
            # Try different methods to kill processes
            if os.name == 'nt':  # Windows
                try:
                    subprocess.run(["taskkill", "/f", "/im", "mcp-proxy.exe"], capture_output=True)
                except Exception as e:
                    print(f"⚠️ Windows process cleanup failed: {e}")
            else:  # Unix/Linux/macOS
                # Try pkill first
                try:
                    subprocess.run(["pkill", "-f", "mcp-proxy"], capture_output=True)
                except Exception as e:
                    print(f"⚠️ pkill failed: {e}")
                    
                    # Try killall as alternative
                    try:
                        subprocess.run(["killall", "mcp-proxy"], capture_output=True)
                    except Exception as e:
                        print(f"⚠️ killall failed: {e}")
                        
                    # Try finding and killing processes using ps and kill
                    try:
                        ps_output = subprocess.check_output(["ps", "-ef"], text=True)
                        for line in ps_output.splitlines():
                            if "mcp-proxy" in line:
                                pid = line.split()[1]
                                try:
                                    subprocess.run(["kill", "-9", pid], capture_output=True)
                                    print(f"Killed process {pid}")
                                except Exception as e:
                                    print(f"⚠️ Failed to kill process {pid}: {e}")
                    except Exception as e:
                        print(f"⚠️ ps/kill method failed: {e}")
            
            # Clear running processes tracking
            self.running_processes.clear()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def _capture_logs_for_duration(self, process, log_file: Path, duration: int = 60):
        """Capture process output for specified duration then redirect to devnull."""
        def stop_logging():
            time.sleep(duration)
            try:
                process.stdout = subprocess.DEVNULL
                process.stderr = subprocess.DEVNULL
            except:
                pass
        
        timer = threading.Timer(duration, stop_logging)
        timer.start()
    
    def _start_single_tool(self, tool: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """Start a single MCP tool."""
        tool_name = tool['name']
        command = tool['command']
        
        try:
            # Check if we're in Cloud Run or similar environment where venv creation might be problematic
            # Use environment variable to control venv creation
            use_venv = os.getenv("MCP_USE_VENV", "false").lower() == "true"
            
            env = os.environ.copy()
            venv_creation_success = False
            
            if use_venv:
                # Create virtual environment
                print(f"🔧 Setting up virtual environment for {tool_name}...")
                venv_path = self.envs_dir / f"{tool_name.replace(' ', '_')}_venv"
                
                # Check if we can create virtual environments
                if not venv_path.exists():
                    try:
                        print(f"🔧 Creating virtual environment for {tool_name}...")
                        subprocess.run(["python", "-m", "venv", str(venv_path)], check=True, capture_output=True)
                        pip_exe = venv_path / ("Scripts/pip.exe" if os.name == 'nt' else "bin/pip")
                        subprocess.run([str(pip_exe), "install", "mcp-proxy"], check=True, capture_output=True)
                        venv_creation_success = True
                    except Exception as e:
                        print(f"⚠️ Failed to create virtual environment: {e}")
                        print("⚠️ Will use system-installed mcp-proxy instead")
                else:
                    venv_creation_success = True
                
                # Set environment
                if venv_creation_success:
                    venv_bin = venv_path / ("Scripts" if os.name == 'nt' else "bin")
                    env["PATH"] = f"{venv_bin}{os.pathsep}{env['PATH']}"
                    env["VIRTUAL_ENV"] = str(venv_path)
            else:
                print(f"🔧 Using system-installed mcp-proxy for {tool_name}...")
            
            # Create log file
            log_file = self.logs_dir / f"{tool_name.replace(' ', '_')}.log"
            
            # Start tool
            print(f"🚀 Starting tool: {command}")
            
            # Make sure log directory exists
            os.makedirs(self.logs_dir, exist_ok=True)
            
            # Try to open log file
            try:
                log_handle = open(log_file, 'w')
                
                # Start process with log file
                process = subprocess.Popen(
                    command.split(),
                    env=env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Capture logs for 1 minute only
                self._capture_logs_for_duration(process, log_file, 60)
                
            except Exception as log_error:
                print(f"⚠️ Failed to open log file: {log_error}")
                print("⚠️ Will redirect output to /dev/null")
                
                # If we can't open the log file, redirect to /dev/null
                process = subprocess.Popen(
                    command.split(),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print(f"✅ Started {tool_name} (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start {tool_name}: {e}")
            return None
    
    def _start_tool_thread(self, tool: Dict[str, Any]):
        """Start a single tool in a separate thread."""
        process = self._start_single_tool(tool)
        if process:
            # Use a lock to safely update the shared dictionary
            self.running_processes[tool['name']] = {
                'process': process,
                'command': tool['command'],
                'port': tool['port']
            }
            print(f"✅ Tool {tool['name']} started successfully")
        else:
            print(f"❌ Failed to start tool {tool['name']}")
    
    def _start_all_tools(self, tools: List[Dict[str, Any]]):
        """Start all MCP tools in parallel."""
        print(f"🚀 Starting {len(tools)} MCP tools in parallel...")
        
        # Create threads for each tool
        threads = []
        for tool in tools:
            thread = threading.Thread(
                target=self._start_tool_thread,
                args=(tool,),
                name=f"tool-starter-{tool['name']}"
            )
            thread.daemon = True  # Make thread a daemon so it exits when main thread exits
            threads.append(thread)
            thread.start()
            print(f"🧵 Started thread for {tool['name']}")
        
        # Wait for all threads to complete (optional, can be removed for fully async operation)
        # for thread in threads:
        #     thread.join()
        
        print("🎉 All MCP tool starter threads launched!")
    
    def _check_log_for_uvicorn(self, log_file: Path) -> bool:
        """Check if log file contains 'Uvicorn running on' message."""
        try:
            if not log_file.exists():
                return False
                
            with open(log_file, 'r') as f:
                content = f.read()
                return "Uvicorn running on" in content
        except Exception as e:
            print(f"⚠️ Error reading log {log_file}: {e}")
            return False
    
    def _check_port_active(self, port: int) -> bool:
        """Check if port is active and listening."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception as e:
            return False
    
    def _check_tool_health(self, tool_name: str) -> Dict[str, Any]:
        """Check health of a single tool."""
        log_file = self.logs_dir / f"{tool_name.replace(' ', '_')}.log"
        
        # Get port from running processes
        port = 0
        if tool_name in self.running_processes:
            port = self.running_processes[tool_name].get('port', 0)
        
        # Check log and port
        log_healthy = self._check_log_for_uvicorn(log_file)
        port_healthy = self._check_port_active(int(port)) if port else False
        is_healthy = log_healthy and port_healthy
        
        return {
            'name': tool_name,
            'port': port,
            'log_healthy': log_healthy,
            'port_healthy': port_healthy,
            'is_healthy': is_healthy,
            'status': '🟢 Healthy' if is_healthy else '🔴 Unhealthy'
        }
    
    def _perform_health_check(self) -> List[Dict[str, Any]]:
        """Perform health check on all running tools."""
        health_results = []
        
        for tool_name in self.running_processes.keys():
            health_result = self._check_tool_health(tool_name)
            health_results.append(health_result)
        
        return health_results
    
    def _print_health_report(self, health_results: List[Dict[str, Any]]):
        """Print formatted health report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n🏥 MCP Health Check Report - {timestamp}")
        print("=" * 60)
        
        if not health_results:
            print("❌ No MCP tools running")
            return
        
        healthy_count = sum(1 for result in health_results if result['is_healthy'])
        total_count = len(health_results)
        
        print(f"📊 Overall Status: {healthy_count}/{total_count} tools healthy")
        print()
        
        for result in health_results:
            name = result['name']
            port = result['port']
            status = result['status']
            log_status = "✅" if result['log_healthy'] else "❌"
            port_status = "✅" if result['port_healthy'] else "❌"
            
            print(f"{status} {name}")
            print(f"   Port: {port} {port_status}")
            print(f"   Log: {log_status}")
            print()
    
    def _stop_single_tool(self, tool_name: str):
        """Stop a single MCP tool."""
        if tool_name in self.running_processes:
            try:
                process = self.running_processes[tool_name]['process']
                process.terminate()
                process.wait(timeout=5)
                print(f"🛑 Stopped {tool_name}")
            except Exception as e:
                print(f"⚠️ Error stopping {tool_name}: {e}")
            finally:
                del self.running_processes[tool_name]
    
    def _detect_tool_changes(self) -> Dict[str, Any]:
        """Detect which specific tools have changed."""
        tools_data = self._get_mcp_tools()
        parsed_tools = self._parse_mcp_tools(tools_data)
        
        # Create new signatures map
        new_signatures = {}
        for tool in parsed_tools:
            new_signatures[tool['name']] = self._get_tool_signature(tool)
        
        # Find changes
        changes = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }
        
        # Check for new and modified tools
        for tool_name, new_sig in new_signatures.items():
            if tool_name not in self.current_tools_signatures:
                # New tool
                tool_data = next(t for t in parsed_tools if t['name'] == tool_name)
                changes['added'].append(tool_data)
            elif self.current_tools_signatures[tool_name] != new_sig:
                # Modified tool
                tool_data = next(t for t in parsed_tools if t['name'] == tool_name)
                changes['modified'].append(tool_data)
            else:
                # Unchanged tool
                tool_data = next(t for t in parsed_tools if t['name'] == tool_name)
                changes['unchanged'].append(tool_data)
        
        # Check for removed tools
        for tool_name in self.current_tools_signatures:
            if tool_name not in new_signatures:
                changes['removed'].append(tool_name)
        
        # Update current signatures
        self.current_tools_signatures = new_signatures
        
        return changes
    
    def _handle_tool_changes(self, changes: Dict[str, Any]):
        """Handle specific tool changes without full restart."""
        total_changes = len(changes['added']) + len(changes['removed']) + len(changes['modified'])
        
        if total_changes == 0:
            return False
        
        print(f"🔄 Detected {total_changes} tool changes:")
        
        # Handle removed tools
        for tool_name in changes['removed']:
            print(f"   ➖ Removing: {tool_name}")
            self._stop_single_tool(tool_name)
        
        # Start modified and new tools in parallel
        threads = []
        
        # Handle modified tools (stop then start)
        for tool in changes['modified']:
            print(f"   🔄 Updating: {tool['name']}")
            self._stop_single_tool(tool['name'])
            
            # Create thread to start the tool
            thread = threading.Thread(
                target=self._start_tool_thread,
                args=(tool,),
                name=f"tool-updater-{tool['name']}"
            )
            thread.daemon = True
            threads.append(thread)
        
        # Handle new tools
        for tool in changes['added']:
            print(f"   ➕ Adding: {tool['name']}")
            
            # Create thread to start the tool
            thread = threading.Thread(
                target=self._start_tool_thread,
                args=(tool,),
                name=f"tool-adder-{tool['name']}"
            )
            thread.daemon = True
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
            print(f"🧵 Started thread for {thread.name}")
        
        # Save state
        state = {
            'last_update': datetime.now().isoformat(),
            'changes': {
                'added': len(changes['added']),
                'removed': len(changes['removed']),
                'modified': len(changes['modified'])
            },
            'total_tools': len(self.running_processes)
        }
        self._save_state(state)
        
        print(f"✅ Tool changes applied successfully!")
        return True
    
    def _scheduled_check(self):
        """Scheduled check for changes and health."""
        try:
            # Check for specific tool changes
            changes = self._detect_tool_changes()
            
            if self._handle_tool_changes(changes):
                # Changes were applied, do a quick health check
                time.sleep(2)  # Give tools time to start
                health_results = self._perform_health_check()
                self._print_health_report(health_results)
            else:
                # No changes, just do health check
                health_results = self._perform_health_check()
                self._print_health_report(health_results)
                
        except Exception as e:
            print(f"❌ Scheduled check failed: {e}")
    
    def start_auto_management(self):
        """Start the auto management system."""
        print("🚀 Starting MCP Auto Manager")
        print(f"📅 Check interval: {self.check_interval} minute(s)")
        print("⏹️  Press Ctrl+C to stop")
        
        # Initial startup
        tools_data = self._get_mcp_tools()
        parsed_tools = self._parse_mcp_tools(tools_data)
        self.current_tools_hash = self._calculate_tools_hash(parsed_tools)
        
        # Initialize tool signatures
        for tool in parsed_tools:
            self.current_tools_signatures[tool['name']] = self._get_tool_signature(tool)
        
        # self._kill_existing_mcp_processes()
        self._start_all_tools(parsed_tools)
        
        # Schedule periodic checks
        schedule.every(self.check_interval).minutes.do(self._scheduled_check)
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds for scheduled tasks
        except KeyboardInterrupt:
            print("\n⏹️  Auto management stopped")
            # self._kill_existing_mcp_processes()


def main():
    """Main function."""
    try:
        # Print environment information for debugging
        print("=" * 50)
        print("MCP Auto Manager Starting")
        print("=" * 50)
        print(f"Python version: {sys.version}")
        print(f"Operating system: {os.name} - {sys.platform}")
        print(f"Current directory: {os.getcwd()}")
        print("=" * 50)
        
        # Create and start manager
        manager = MCPAutoManager()
        manager.start_auto_management()
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
