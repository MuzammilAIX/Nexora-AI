from pathlib import Path

p = Path("src/App.tsx")
content = p.read_text(encoding="utf-8")

# Add import
if "import { Assistant }" not in content:
    content = content.replace(
        "import { CRM } from './pages/CRM'",
        "import { CRM } from './pages/CRM'\nimport { Assistant } from './pages/Assistant'"
    )

# Replace the placeholder route
if '<Route path="/assistant" element={<Placeholder title="AI Assistant"' in content:
    # Extract the line and replace it
    lines = content.split("\\n")
    new_lines = []
    for line in lines:
        if '<Route path="/assistant"' in line:
            new_lines.append('              <Route path="/assistant" element={<Assistant />} />')
        else:
            new_lines.append(line)
    content = "\\n".join(new_lines)

p.write_text(content, encoding="utf-8")
print("App.tsx updated with Assistant route")
