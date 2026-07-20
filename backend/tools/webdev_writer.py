import os
import json
from pathlib import Path
from typing import List, Dict, Any
from backend.config import GENERATED_APPS_DIR
from backend.schemas import FileManifestItem

def get_project_dir(project_id: str) -> Path:
    """
    Resolves and validates the workspace directory path for a given project identifier.
    
    Args:
        project_id (str): The unique identifier for the project workspace.
        
    Returns:
        Path: Resolved absolute Path object pointing to the project directory.
        
    Raises:
        ValueError: If project_id is invalid or attempts path traversal outside GENERATED_APPS_DIR.
    """
    if not project_id or not isinstance(project_id, str):
        raise ValueError("Invalid or empty project_id provided.")
    target_dir = (GENERATED_APPS_DIR / project_id).resolve()
    # Security check: Ensure target_dir is strictly inside GENERATED_APPS_DIR
    if not str(target_dir).startswith(str(GENERATED_APPS_DIR.resolve())):
        raise ValueError(f"Security Sandbox Violation: Path traversal attempt detected for project_id: {project_id}")
    return target_dir

def create_workspace_directory(project_id: str) -> Dict[str, Any]:
    """
    Initializes a clean local filesystem workspace directory for a generated application.
    
    Args:
        project_id (str): The unique project identifier.
        
    Returns:
        Dict[str, Any]: Structured outcome containing status ('success' or 'error'), workspace_path, and guided recovery instructions.
    """
    try:
        project_dir = get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return {
            "status": "success",
            "workspace_path": str(project_dir),
            "message": f"Successfully initialized workspace directory for project '{project_id}'."
        }
    except ValueError as val_err:
        return {
            "status": "error",
            "error_type": "SecurityViolation",
            "error_message": str(val_err),
            "recovery_instruction": "Sanitize project_id string to remove relative directory components ('..', '/', '\\') and re-call tool."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "IOError",
            "error_message": f"Failed to create workspace directory: {str(e)}",
            "recovery_instruction": "Ensure write permissions exist for generated-apps directory and retry creation."
        }

def write_file(project_id: str, relative_path: str, content: str) -> Dict[str, Any]:
    """
    Creates or writes content to a file safely within the project's sandbox directory.
    
    Args:
        project_id (str): The unique project identifier.
        relative_path (str): Relative file path within the workspace (e.g. 'src/App.jsx', 'index.html').
        content (str): The string or code content to write into the destination file.
        
    Returns:
        Dict[str, Any]: Structured dictionary result containing file_path, bytes_written, status, and guided error recovery instructions.
    """
    try:
        project_dir = get_project_dir(project_id)
        file_path = (project_dir / relative_path).resolve()
        
        if not str(file_path).startswith(str(project_dir)):
            return {
                "status": "error",
                "error_type": "PathTraversalViolation",
                "error_message": f"Security Sandbox Violation: relative_path '{relative_path}' attempts to escape project directory.",
                "recovery_instruction": "Ensure relative_path is a relative path inside the project workspace (e.g. 'src/App.jsx', 'index.html')."
            }
            
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return {
            "status": "success",
            "file_path": relative_path,
            "bytes_written": len(content),
            "message": f"Successfully wrote file: {relative_path} ({len(content)} bytes)"
        }
    except ValueError as val_err:
        return {
            "status": "error",
            "error_type": "InvalidProjectID",
            "error_message": str(val_err),
            "recovery_instruction": "Provide a valid alphanumeric project_id identifier."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "FileWriteError",
            "error_message": f"Could not write file '{relative_path}': {str(e)}",
            "recovery_instruction": "Check disk space and filesystem write permissions, then retry file writing step."
        }

def scaffold_base_template(project_id: str, app_name: str, tagline: str) -> Dict[str, Any]:
    """
    Scaffolds base React/HTML single-page app boilerplate including package manifest, index.html, and CSS design system.
    
    Args:
        project_id (str): The unique project identifier.
        app_name (str): Human-readable name of the application.
        tagline (str): Short marketing description or value proposition tagline.
        
    Returns:
        Dict[str, Any]: Execution status dictionary with created file count and guided error recovery instructions.
    """
    try:
        ws_res = create_workspace_directory(project_id)
        if ws_res.get("status") == "error":
            return ws_res
        
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

        # 3. index.html
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
        app_jsx = f"""const {{ useState }} = React;

function App() {{
  return (
    <div style={{{{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}}}>
      <header style={{{{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}}}>
        <h1 style={{{{ fontSize: '2rem', color: '#60a5fa' }}}}>{app_name}</h1>
        <button className="btn">Get Started</button>
      </header>
      <main className="card">
        <p>{tagline}</p>
      </main>
    </div>
  );
}}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
"""
        write_file(project_id, "src/App.jsx", app_jsx)
        
        return {
            "status": "success",
            "message": f"Base scaffold created for {app_name} ({project_id})"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "ScaffoldError",
            "error_message": f"Scaffold creation failed: {str(e)}",
            "recovery_instruction": "Ensure clean workspace path and retry scaffold_base_template."
        }

def generate_manifest(project_id: str) -> List[FileManifestItem]:
    """
    Scans the workspace directory for a project and builds a file manifest.
    
    Args:
        project_id (str): The unique project identifier.
        
    Returns:
        List[FileManifestItem]: List of FileManifestItem objects representing created workspace assets.
    """
    manifest = []
    try:
        project_dir = get_project_dir(project_id)
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
    except Exception:
        pass
    return manifest
