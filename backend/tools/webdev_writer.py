import os
import json
from pathlib import Path
from typing import List, Dict, Any
from backend.config import GENERATED_APPS_DIR
from backend.schemas import FileManifestItem, AppBuildArtifact

def get_project_dir(project_id: str) -> Path:
    target_dir = (GENERATED_APPS_DIR / project_id).resolve()
    # Security check: Ensure target_dir is strictly inside GENERATED_APPS_DIR
    if not str(target_dir).startswith(str(GENERATED_APPS_DIR.resolve())):
        raise ValueError(f"Invalid path traversal attempt for project_id: {project_id}")
    return target_dir

def create_workspace_directory(project_id: str) -> str:
    """
    Initializes a clean local filesystem workspace directory for a generated application.
    
    Args:
        project_id: The unique project identifier.
        
    Returns:
        Absolute path to the workspace directory.
    """
    project_dir = get_project_dir(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    return str(project_dir)

def write_file(project_id: str, relative_path: str, content: str) -> str:
    """
    Creates or writes content to a file safely within the project's sandbox directory.
    
    Args:
        project_id: The unique project identifier.
        relative_path: Path relative to the project directory (e.g., 'src/App.jsx' or 'index.html').
        content: The code or string content to write into the file.
        
    Returns:
        Confirmation message with path.
    """
    project_dir = get_project_dir(project_id)
    file_path = (project_dir / relative_path).resolve()
    
    if not str(file_path).startswith(str(project_dir)):
        raise ValueError(f"Path traversal detected in relative_path: {relative_path}")
        
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Successfully wrote file: {relative_path} ({len(content)} bytes)"

def scaffold_base_template(project_id: str, app_name: str, tagline: str) -> str:
    """
    Scaffolds base React/HTML single-page app boilerplate including package manifest, index.html, and CSS design system.
    
    Args:
        project_id: The unique project identifier.
        app_name: Name of the application.
        tagline: Tagline or description.
        
    Returns:
        Status message.
    """
    create_workspace_directory(project_id)
    
    # 1. package.json
    package_json = {
        "name": app_name.lower().replace(" ", "-"),
        "version": "1.0.0",
        "description": tagline,
        "main": "index.html",
        "scripts": {
            "start": "serve ."
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "lucide-react": "^0.263.1"
        }
    }
    write_file(project_id, "package.json", json.dumps(package_json, indent=2))
    
    # 2. styles.css - High Quality Design Tokens
    styles_css = """/* Base Design Tokens & Reset */
:root {
  --bg-primary: #090d16;
  --bg-card: rgba(15, 23, 42, 0.75);
  --bg-card-hover: rgba(30, 41, 59, 0.85);
  --border-color: rgba(255, 255, 255, 0.1);
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --accent-primary: #3b82f6;
  --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  --accent-success: #10b981;
  --font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: var(--font-family);
  min-height: 100vh;
  line-height: 1.6;
}

#root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Common UI Components */
.btn {
  background: var(--accent-gradient);
  color: #fff;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4);
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.card:hover {
  background: var(--bg-card-hover);
  border-color: rgba(59, 130, 246, 0.3);
}

.tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
}
"""
    write_file(project_id, "styles.css", styles_css)

    # 3. index.html - Live React Render Container with Error Boundary
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{app_name} - Prototype</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body>
  <div id="root"></div>

  <!-- Runtime Error Catching -->
  <div id="error-boundary" style="display:none; padding: 2rem; color: #ef4444; background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; margin: 2rem;">
    <h3>Prototype Runtime Warning</h3>
    <pre id="error-message"></pre>
  </div>

  <script>
    window.onerror = function(msg, url, line) {{
      const errBox = document.getElementById('error-boundary');
      if (errBox) {{
        errBox.style.display = 'block';
        document.getElementById('error-message').textContent = msg + ' (Line ' + line + ')';
      }}
    }};
  </script>

  <script type="text/babel" src="src/App.jsx"></script>
</body>
</html>
"""
    write_file(project_id, "index.html", index_html)

    # 4. src/App.jsx default fallback
    app_jsx = f"""const {{ useState, useEffect }} = React;

function App() {{
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div style={{{{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}}}>
      <header style={{{{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', pb: '1rem' }}}}>
        <div>
          <h1 style={{{{ fontSize: '2rem', background: 'linear-gradient(135deg, #60a5fa, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}}}>{app_name}</h1>
          <p style={{{{ color: '#94a3b8' }}}}>{tagline}</p>
        </div>
        <button className="btn">Get Started</button>
      </header>

      <main className="card" style={{{{ textAlign: 'center', padding: '4rem 2rem' }}}}>
        <h2 style={{{{ marginBottom: '1rem' }}}}>Welcome to {app_name}</h2>
        <p style={{{{ color: '#94a3b8', maxWidth: '600px', margin: '0 auto 2rem auto' }}}}>
          This dynamic interactive prototype was autonomously generated based on deep market analysis and product specs.
        </p>
      </main>
    </div>
  );
}}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
"""
    write_file(project_id, "src/App.jsx", app_jsx)
    
    return f"Base scaffold created for {app_name} ({project_id})"

def generate_manifest(project_id: str) -> List[FileManifestItem]:
    """
    Scans the workspace directory for a project and builds a file manifest.
    
    Args:
        project_id: The unique project identifier.
        
    Returns:
        List of FileManifestItem objects.
    """
    project_dir = get_project_dir(project_id)
    manifest = []
    
    if not project_dir.exists():
        return manifest
        
    for root, dirs, files in os.walk(project_dir):
        for file in files:
            full_path = Path(root) / file
            rel_path = str(full_path.relative_to(project_dir))
            size = full_path.stat().st_size
            ext = full_path.suffix.lstrip(".").lower() or "txt"
            manifest.append(FileManifestItem(
                file_path=rel_path,
                file_size_bytes=size,
                file_type=ext
            ))
            
    return manifest
