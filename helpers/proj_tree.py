import os

ROOT = "."

ALLOWED = {".py", ".html", ".css", ".js", ".log", '.md'}

IGNORE_DIRS = {"__pycache__", ".git", ".idea", "venv", "env", ".github", ".vscode", "raw_html", "stores_programs_terms"}

def walk(dir_path, prefix=""):
    entries = sorted(os.listdir(dir_path))

    for i, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)

        if os.path.isdir(path):
            if entry in IGNORE_DIRS:
                continue

            print(prefix + "📁 " + entry)
            walk(path, prefix + "  ")

        else:
            ext = os.path.splitext(entry)[1]

            if ext not in ALLOWED:
                continue

            print(prefix + "📄 " + entry)

walk(ROOT)
