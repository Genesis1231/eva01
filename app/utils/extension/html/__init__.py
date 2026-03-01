import os

def load_html(template: str, **kwargs) -> str:

    dir = os.path.dirname(__file__)
    html_path = os.path.join(dir, template)
    
    try:
        with open(html_path, 'r') as f:
            html = f.read().strip()
    
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file {html_path} not found.")
    
    for key, value in kwargs.items():
        html = html.replace(f"<{key}>", value)
        
    return html