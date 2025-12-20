from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

import schedule
import psutil
import time
import supabase
import os
import re
import copy
import logging

# Configure logging
logger = logging.getLogger(__name__)
import time

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")

# Predefined company ID
PREDEFINED_COMPANY_ID = "95901eaa-c08d-4b0a-a5d6-3063a622cb98"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and key must be provided in environment variables")

# Initialize Supabase client
supabase: Client = create_client(
    supabase_url= SUPABASE_URL,
    supabase_key= SUPABASE_KEY
)

# Cache for tools information to reduce Supabase calls
_tools_cache = None
_last_cache_time = 0
_cache_ttl = 60  # Cache TTL in seconds

# Track tool restart attempts to avoid frequent restarts
_tool_restart_attempts = {}  # tool_id -> last_attempt_time
_restart_cooldown = 15 * 60  # 15 minutes in seconds

# Track tool restart attempts to avoid frequent restarts
_tool_restart_attempts = {}  # tool_id -> last_attempt_time
_restart_cooldown = 15 * 60  # 15 minutes in seconds

# Fetch all tools information from Supabase with caching
def get_tools_info():
    global _tools_cache, _last_cache_time
    
    current_time = time.time()
    
    # Return cached data if it's still valid
    if _tools_cache is not None and (current_time - _last_cache_time) < _cache_ttl:
        print(f"Using cached tools info ({len(_tools_cache)} tools)")
        return _tools_cache
    
    try:
        print("Fetching tools info from Supabase...")
        response = supabase.table('tools_with_decrypted_keys').select("*").execute()
        
        if response.data is None:
            return []
            
        # Update cache
        _tools_cache = response.data
        _last_cache_time = current_time
        
        print(f"Updated tools cache with {len(_tools_cache)} tools")
        return _tools_cache
    except Exception as e:
        print(f"[ERROR] Failed to fetch tools info from Supabase: {e}")
        # If we have cached data, return it even if it's expired
        if _tools_cache is not None:
            print(f"Using expired cached data due to fetch error")
            return _tools_cache
        return []

# Get running processes information based on the specified list of ports
def get_ports_info(ports):
    result = []
    port_list = []

    cached_connections = psutil.net_connections(kind='inet')

    for conn in cached_connections:
        if conn.status == psutil.CONN_LISTEN and conn.laddr.port in ports:
            port = conn.laddr.port
            pid = conn.pid
            try:
                process = psutil.Process(pid)
                cmdline = process.cmdline()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                cmdline = []

            port_list.append(port)
            result.append(cmdline)

    return dict(zip(port_list, result))

# Perform batch update to Supabase for tools' status
def update_tools_info_batch(updates):
    # Break updates into smaller batches to avoid timeouts
    batch_size = 5  # Process 5 tools at a time
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} of {(len(updates) + batch_size - 1) // batch_size}")
        
        max_retries = 3
        for retry in range(max_retries):
            try:
                supabase.table('tools').upsert(batch, on_conflict="tool_id").execute()
                print(f"Successfully updated batch {i//batch_size + 1}")
                break  # Success, exit retry loop
            except Exception as e:
                if "timeout" in str(e).lower() and retry < max_retries - 1:
                    wait_time = (retry + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                    print(f"[WARNING] Timeout updating batch {i//batch_size + 1}, retrying in {wait_time}s ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"[ERROR] Failed to update tools info in Supabase: {e}")
                    break  # Non-timeout error or max retries reached

# Remove extra spaces from a string
def remove_double_space(original_string):
    result = re.sub(r'\s+', ' ', original_string).strip()
    return result

# Safely extract the port value from a nested dictionary structure
def safe_get_port(row):
    try:
        return int(row['versions'][0]['released']['port'])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

# Function to start a tool that should be running but isn't
def start_tool(tool):
    """Start a tool that should be running but isn't in a non-blocking way."""
    # Run the actual tool start in a separate thread
    def run_tool_start():
        try:
            if 'versions' not in tool or not tool['versions']:
                logger.warning(f"Cannot start tool: no versions found for tool {tool.get('name', 'unknown')}")
                return
                
            version = tool['versions'][0]
            if 'released' not in version or not version['released']:
                logger.warning(f"Cannot start tool: no released version found for tool {tool.get('name', 'unknown')}")
                return
                
            released = version['released']
            port = released.get('port', '')
            args = released.get('args', '')
            env = released.get('env', {})
            
            if not port or not args:
                logger.warning(f"Cannot start tool: missing port or args for tool {tool.get('name', 'unknown')}")
                return
                
            # Convert env dict to command line args
            env_str = " ".join(f"-e {k} {v}" for k, v in env.items())
            if env_str:
                env_str += " "
                
            # Construct the full command
            cmd = f"mcp-proxy --sse-port={port} {env_str}-- {args}".replace("  ", " ")
            
            logger.info(f"Starting tool '{tool.get('name', 'unknown')}' with command: {cmd}")
            
            # Start the process
            import subprocess
            import os
            
            env_vars = os.environ.copy()
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env_vars
            )
            
            # Start a thread to read output
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        logger.info(f"[{timestamp}][Tool {tool.get('name', 'unknown')}] {line.strip()}")
            
            import threading
            output_thread = threading.Thread(target=read_output)
            output_thread.daemon = True
            output_thread.start()
            
            logger.info(f"Tool '{tool.get('name', 'unknown')}' started successfully")
            
        except Exception as e:
            logger.error(f"Error starting tool '{tool.get('name', 'unknown')}': {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Start the tool in a separate thread
    import threading
    tool_thread = threading.Thread(target=run_tool_start)
    tool_thread.daemon = True
    tool_thread.start()
    
    return True  # Return immediately, actual start happens in background

# Main function to check the status of each tool
def check_tools_status():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Tools status check started at: {current_time}")

    # Get tools info (cached if possible)
    tools_info = get_tools_info()
    
    # Extract ports only once
    all_ports = [safe_get_port(row) for row in tools_info if safe_get_port(row) is not None]
    
    # Skip processing if no tools have ports
    if not all_ports:
        print("No tools with ports found, skipping status check")
        return
        
    # Get port info in one batch
    ports_info = get_ports_info(all_ports)

    updates = []
    tools_to_start = []
    
    # Pre-calculate the predefined company ID check
    is_predefined_company = lambda company_id: company_id == PREDEFINED_COMPANY_ID

    for row in tools_info:
        tool_id = row['tool_id']
        company_id = row['company_id']
        current_status = row.get('on_status', '')
        
        # Skip updating status if it's manually turned off by the user
        if current_status != "Offline":
            port = safe_get_port(row)
            
            # Check if tool belongs to the predefined company and has environment variables
            is_predefined = company_id == PREDEFINED_COMPANY_ID
            has_env_vars = False
            
            if is_predefined and 'versions' in row and row['versions']:
                for version in row['versions']:
                    if 'released' in version and version['released'] and 'env' in version['released']:
                        env_vars = version['released']['env']
                        if env_vars and isinstance(env_vars, dict) and len(env_vars) > 0:
                            has_env_vars = True
                            break
            
            if port is None:
                status = "Inactive"
              
            else:
                try:
                    expected_args = row['versions'][0]['released']['args']
                    if port not in ports_info:
                        status = f"Inactive, Port {port} not found in running processes"
                        print(f"Port {port} for tool '{row['name']}' (ID: {tool_id}) not found in running processes.")
                        
                        # Check if we should try to restart this tool
                        current_time = time.time()
                        last_attempt = _tool_restart_attempts.get(tool_id, 0)
                        time_since_last_attempt = current_time - last_attempt
                        
                        # Add to list of tools to start if:
                        # 1. It's not predefined or offline
                        # 2. It's been at least _restart_cooldown seconds since last attempt
                        if (not is_predefined and
                            current_status != "Offline" and
                            current_status != "Predefined" and
                            time_since_last_attempt >= _restart_cooldown):
                            
                            tools_to_start.append(row)
                            # Update the last attempt time
                            _tool_restart_attempts[tool_id] = current_time
                            print(f"Scheduling restart for tool '{row['name']}' (ID: {tool_id}) after {time_since_last_attempt:.1f}s since last attempt")
                        elif time_since_last_attempt < _restart_cooldown:
                            print(f"Skipping restart for tool '{row['name']}' (ID: {tool_id}), cooldown period active ({time_since_last_attempt:.1f}s/{_restart_cooldown}s)")
                    else:
                        cmdline = ports_info[port]
                        cmdline_str = remove_double_space(" ".join(cmdline))

                        if remove_double_space(expected_args) in cmdline_str:
                            status = "Online"
                        else:
                            if cmdline_str:
                                status = f"Inactive, Port is used by: {cmdline_str}"
                            else:
                                status = "Inactive, Port is used by an unknown or inaccessible process"
                except (KeyError, IndexError) as e:
                        status = f"Inactive, Port Problem: {type(e).__name__} - {e}"
                        print(f"Error in checking tool status for tool '{row.get('name', 'unknown')}' (ID: {tool_id}), port {port}: {type(e).__name__} - {e}")
            
            # After all port checks, override status for predefined tools with env vars
            if is_predefined and has_env_vars:
                status = "Predefined"

            updates.append({
                "tool_id": tool_id,
                "on_status": status,
                "name": row["name"],
                "versions": row.get("versions")  # Include the updated versions data
            })
        else:
            # For manually turned off tools, only update the necessary fields
            # to preserve the turned off status, without modifying other data
            status = "Offline"
            # Clear port field for offline tools
            if 'versions' in row and row['versions'] and 'released' in row['versions'][0]:
                # Create a deep copy of versions to avoid reference issues
                versions_copy = copy.deepcopy(row['versions'])
                versions_copy[0]['released']['port'] = ""
                row['versions'] = versions_copy
            
            updates.append({
                "tool_id": tool_id,
                "on_status": status,
                "name": row["name"],
                "versions": row.get("versions")  # Include the updated versions data
            })
            
    # Update tool statuses in Supabase
    update_tools_info_batch(updates)
    
    # Start tools that should be running but aren't
    if tools_to_start:
        print(f"Starting {len(tools_to_start)} tools that should be running...")
        for tool in tools_to_start:
            start_tool(tool)


# Schedule status check to run every 1 minute
schedule.every(1).minutes.do(check_tools_status)

# Also schedule an immediate check after adding a new tool
def check_after_adding():
    """Run a check immediately after adding a new tool in a non-blocking way"""
    print("Scheduling immediate check after adding a new tool...")
    
    # Run the check in a separate thread to avoid blocking
    def run_check():
        try:
            print("Running immediate tool status check in background thread...")
            check_tools_status()
        except Exception as e:
            print(f"Error in background tool status check: {e}")
            import traceback
            traceback.print_exc()
    
    # Start the check in a separate thread
    import threading
    check_thread = threading.Thread(target=run_check)
    check_thread.daemon = True  # Thread will exit when main program exits
    check_thread.start()

# When running as a standalone script
if __name__ == "__main__":
    # Run an initial check in a non-blocking way
    print("Running initial tools status check...")
    
    # Run the initial check in a separate thread to avoid blocking
    def run_initial_check():
        try:
            check_tools_status()
        except Exception as e:
            print(f"Error in initial check: {e}")
            import traceback
            traceback.print_exc()
    
    # Start the initial check in a separate thread
    import threading
    initial_check_thread = threading.Thread(target=run_initial_check)
    initial_check_thread.daemon = True
    initial_check_thread.start()
    
    # Run the scheduled tasks continuously
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Program stopped manually.")