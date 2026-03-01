import os
from config import logger
import subprocess
import platform
from typing import Dict, Type

import cv2
import pyautogui
from pydantic import BaseModel, Field
from langchain_community.tools import BaseTool
from utils.vision import Describer
 

class ScreenshotInput(BaseModel):
    query: str = Field(description="Input for Screenshot tool. Concisely define the desired information.")
    
class Screenshot(BaseTool):
    """Tool that captures a screenshot and analyzes the content."""
    
    name: str = "screenshot_tool"
    description: str = "Tool for capturing and analyzing the computer screenshot."
    type: str = "conversational"
    client: str = "desktop"
    args_schema: Type[BaseModel] = ScreenshotInput
    
    def _run(
        self,
        query: str,
    ) -> Dict:
        filename = f"screenshot.jpg"
        full_path = os.path.join(os.path.dirname(__file__), "temp", filename)
        
        try:
            if platform.system() == "Linux" and os.path.exists("/mnt/c"): # check if the system is WSL
                self.wsl_screenshot(full_path)
            else:
                screenshot = pyautogui.screenshot()
                screenshot.save(full_path)
                
            image = cv2.imread(full_path)
            describer = Describer("chatgpt") # Chatgpt 4o-mini is the best model for the describer
            analysis = describer.analyze_screenshot(image_data=image, query=query)
            content = f"I took a screenshot and found the following information: {analysis}"
            
        except Exception as e:
            logger.error(f"Failed to analyze screenshot {str(e)}.")
            return {"error": f"Failed to analyze screenshot {str(e)}."}
            
        return  {"action": content }
    
    def wsl_screenshot(self, file_path: str) -> str:
        """ Take a screenshot using WSL and save it as JPG """
        windows_path = subprocess.check_output(["wslpath", "-w", file_path]).decode().strip()
    
        # PowerShell command to take a full screenshot using PrintScreen and save it as JPG
        ps_command = f'''
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen
            $bounds = $screen.Bounds
            [System.Windows.Forms.SendKeys]::SendWait("%{{PRTSC}}")
            Start-Sleep -Milliseconds 250
            $bitmap = [System.Windows.Forms.Clipboard]::GetImage()
            if ($bitmap -ne $null) {{
                $bitmap.Save('{windows_path}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
                [System.Windows.Forms.Clipboard]::Clear()
            }} 
        '''
        subprocess.run(["powershell.exe", "-Command", ps_command], capture_output=True, text=True)
