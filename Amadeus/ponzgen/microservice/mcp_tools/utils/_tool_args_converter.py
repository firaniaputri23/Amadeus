def _env_to_str(env_dict):
    return " ".join(f"-e {k} {v}" for k, v in env_dict.items())

def tool_args_converter(tools):
    arr_dict_tools_cmd = []
    for tool in tools:
        try:
            # Extract the most recent version and its config
            tool_cfg = tool["versions"][-1]["released"]
            args = tool_cfg.get("args", "")
            port_value = tool_cfg.get("port", "")
            
            # Ensure port is a valid integer string
            try:
                # Attempt to convert to int to validate, then back to string
                port = str(int(port_value)) if port_value else ""
            except (ValueError, TypeError):
                print(f"Invalid port value: {port_value} for tool {tool.get('name', 'unknown')}. Skipping tool.")
                continue
                
            required_env = tool_cfg.get("required_env", "")
            env = tool_cfg.get("env", {})
            
            # If the env is not empty, convert it to a string
            if env:
                env_str = _env_to_str(env)
                env_str += " "
            else:
                env_str = ""

        except Exception as e:
            print(f"Error processing tool {tool['tool_id']}: {e}")
            continue
        
        dict_tool = {
            "full_cmd": f"mcp-proxy --sse-port={port} {env_str}-- {args}".replace("  ", " "),
            "required_env": required_env,
        }
        arr_dict_tools_cmd.append(dict_tool)
    
    return arr_dict_tools_cmd

if __name__ == "__main__":
    tools = [
        {'tool_id': '06d02547-6e18-48cd-84b5-439cff6680e1', 'name': '', 'description': '', 'versions': []},
        {'tool_id': '2a196aee-f9de-42fe-bbcd-acd5bd262f2f', 'name': 'test', 'description': '', 'versions': []},
        {'tool_id': 'db82cb7f-3dae-4847-beec-3149df093ed6', 'name': '123', 'description': '123', 'versions': [{'version': '123', 'released': '2025-03-19'}]},
        {'tool_id': 'e304c741-357e-4e8e-ab62-75ec33ae3fd7', 'name': 'fetch_mcp', 'description': 'test', 'versions': [{
            'version': '1', 'released': {
                'env': {'test333': 'test123'}, 'args': 'uvx mcp-server-fetch', 'port': '10001', 'method': 'sse', 'version': '1.0.0', 'required_env': ['test123']
            }}]
        }
    ]

    # Call the function to convert the tools' configuration into commands
    arr_dict_tools_cmd = tool_args_converter(tools)
    for dict_tool_cmd in arr_dict_tools_cmd:
        print(dict_tool_cmd)
