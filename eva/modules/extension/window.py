from config import logger
import os
import atexit
import webbrowser
from pathlib import Path

class Window:
    """
    Window class to open a new window with HTML content or a URL.
    
    Methods:
    - launch_html: Open a new window with HTML content.
    - launch_url: Open a new window with a URL.
    
    """
    def __init__(self):
        self.browser = None
        self._window_width = 450
        self._window_height = 600
        self._temp_files = []
        
        # Create ~/.eva/temp directory
        self._temp_dir = self._get_temp_dir()
        atexit.register(self._cleanup_temp_files)
    
    @staticmethod   
    def _get_temp_dir() -> str:
        """Get or create the EVA temp directory"""
        
        temp_dir = Path.home() / '.eva' / 'html'
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        return str(temp_dir)
        
    def launch_html(
        self, 
        html_content, 
        new: bool = False
    )-> None:
        """ Launch a new window with HTML content """
        
        # Generate unique filename in ~/.eva/temp
        temp_filename = f'window_{os.urandom(8).hex()}.html'
        temp_path = os.path.join(self._temp_dir, temp_filename)
        self._temp_files.append(temp_path)
        
        html_content = html_content.replace("</title>", 
            f"</title><script type='text/javascript'>window.onload = window.resizeTo({self._window_width}, {self._window_height}); </script>")
        
        with open(temp_path, 'w', encoding='utf-8') as file:
            file.write(html_content)

        # Open the html in the default web browser
        if not self.browser:
            self.browser = webbrowser.get()
        self.browser.open(f'file://{temp_path}', new=1 if new else 0)

    def launch_url(
        self, 
        url: str, 
        new: bool = False
    )-> None:
        """ Launch a new window with a URL """
        
        window_index = 1 if new else 0
        
        if not self.browser:
            self.browser = webbrowser.get() 
        
        self.browser.open(url, new=window_index)

    def _cleanup_temp_files(self):
        """Clean up temporary files when the program exits"""
        for temp_file in self._temp_files:
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file}: {e}")

        