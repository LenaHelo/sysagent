import os
import subprocess
import re
from typing import Optional

def extract_man_text(command: str, section: str) -> str:
    """
    Extracts the raw text from a Linux man page, stripping terminal formatting.
    """
    args = ["man", "-Tutf8", section, command]
    
    try:
        result = subprocess.run(
            args, 
            capture_output=True, 
            text=True, 
            check=True,
            # Force a massive width to prevent arbitrary line-wrapping which ruins chunking
            env={"MANWIDTH": "10000", **os.environ} 
        )
        raw_text = result.stdout
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to extract man page for {command} ({section}): {e.stderr}")

    # Strip backspace overstriking (e.g., '_\bH' or 'H\bH' used for bold/underline)
    clean_text = re.sub(r'.\x08', '', raw_text)
    
    # Strip ANSI escape codes
    clean_text = re.sub(r'\x1b\[[0-9;]*[mK]', '', clean_text)
    
    # Strip extreme whitespace padding while preserving newlines
    clean_text = "\n".join(line.rstrip() for line in clean_text.splitlines())
    
    return clean_text.strip()

def get_man_pages_in_section(section: str) -> list[str]:
    """
    Finds all available man pages for a given section by scanning standard directories.
    Returns a list of command names (e.g., ['ls', 'grep']).
    """
    standard_paths = [
        f"/usr/share/man/man{section}",
        f"/usr/local/share/man/man{section}"
    ]
    
    commands = set()
    for path in standard_paths:
        if os.path.exists(path):
            for filename in os.listdir(path):
                # Match files like 'ls.1.gz' or 'dmesg.8'
                if filename.endswith(f".{section}.gz") or filename.endswith(f".{section}"):
                    cmd_name = filename.split(f".{section}")[0]
                    commands.add(cmd_name)
                    
    return sorted(list(commands))
