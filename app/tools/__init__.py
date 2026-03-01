import os
from config import logger
import importlib
import inspect
import json
from typing_extensions import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# from langchain_community.tools import DuckDuckGoSearchRun
# from langchain_community.tools import WikipediaQueryRun
from langchain_community.tools import TavilySearchResults 

class ToolManager:
    """
    ToolManager is a class that manages all the tools in the system.
    
    Attributes:
        tools: List of tools
        tool_map: Dictionary of tool name to tool object
        client: the client that the tools are available for
    
    Methods:
        get_tools: return the tools
        get_tools_info: return the tools and their descriptions
        import_tools_from_folder: import all classes from the tools folder
        initialize_tools: initialize all the tools
        execute: execute a list of actions 
    """
    def __init__(self, client: str)-> None:
        self.client: str = client.lower()
        self.tools: List[Any] = self.initialize_tools()
        self.tool_map: Dict[str, Any] = {tool.name: tool for tool in self.tools}
    
    def get_tools(self)-> List[Any]:
        return self.tools
    
    def get_tools_info(self)-> str:
        """ get the tools and their descriptions """
        tool_info = []
        for tool in self.tools:
            tool_schema = {
                "name" : tool.name,
                "description": tool.description,
                # "args_schema": { "title": "query", "type": "string" } # simplify it for now
                "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else { "title": "query", "type": "string" }
                }
            tool_info.append(tool_schema)
        
        # print("All available tools: ", tool_info)
        return json.dumps(tool_info)
    
    def import_tools_from_folder(self) -> List[Any]:
        """ Import all classes from the tools folder """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        imported_tools = []        
        for filename in os.listdir(current_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                try: 
                    # Import the module
                    module = importlib.import_module(f'.{module_name}', package=__package__)
                    class_obj = getattr(module, module_name.capitalize())
                    if inspect.isclass(class_obj):
                        # Only load the tools that are available for the client, built in tools do not have client attribute
                        tool = class_obj()
                        if not hasattr(tool, 'client') or tool.client.upper() == "ALL" or tool.client.upper() == self.client: 
                            imported_tools.append(tool)
                            
                except Exception as e:
                    logger.error(f"Error importing {module_name}: {str(e)}")
                        
        return imported_tools 

    def initialize_tools(self) -> List[Any]:
        """ Initialize all the tools """
        all_tools = self.import_tools_from_folder()
        
        # Add built-in tools
        search_tool = TavilySearchResults(
            max_results=3,
        )
        # wikipedia_tool = WikipediaQueryRun()
        
        built_in_tools = [
            search_tool,  # tool to search the internet
        ]
            
        all_tools.extend(built_in_tools)
        
        return all_tools
    
    def execute(self, client, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ Execute a list of actions """
        
        def execute_tool(action: Dict[str, Any]) -> Dict[str, Any]:
            """ Execute the tool with the given args """
            tool_name: str = action.get("name")
            args: Dict = action.get("args", {})
            tool = self.tool_map.get(tool_name)
            
            try:
                result = tool.run(args)                      
            except Exception as e:
                logger.error(f"Failed to execute tool {tool_name}: {str(e)}")
                return {"error": f"Error executing {tool_name}: {str(e)}"}
            
            if hasattr(tool, 'run_client') and not result.get("error"): # run the client function if available and no error
                client_results = tool.run_client(client, **result)
                if client_results:
                    result["additional"] = client_results
                        
            return {"result": result}
        
        with ThreadPoolExecutor() as executor:
            return list(executor.map(execute_tool, actions))
        


