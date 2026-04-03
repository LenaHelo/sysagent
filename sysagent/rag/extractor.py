import os
import subprocess
import re
from typing import Optional

def extract_man_text(command: str, section: str) -> str:
    """
    Extracts the raw text from a Linux man page and removes terminal formatting.
    
    This acts as the "Reader" in the RAG ingestion pipeline. It calls the system's `man` 
    command and forces UTF-8 plain text output. Since groff (the man page formatter) 
    uses raw terminal control characters to simulate bolding and underlining, this 
    function performs regex passes to strip backspace overstriking and ANSI color 
    codes, returning clean English text suitable for vector embedding.

    Args:
        command (str): The name of the command to retrieve (e.g., "ls").
        section (str): The manual section where the command lives (e.g., "1").

    Returns:
        str: The clean, unformatted strings of the man page contents.
        
    Raises:
        ValueError: If the command does not have a manual entry in the specified section.
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

    # Strip man page header/footer lines.
    # These are repeated decorative lines like: "LS(1)   User Commands   LS(1)"
    # They always contain the command name in parentheses and appear at the top and bottom
    # of each paginated block. They carry zero semantic value for embedding.
    header_footer_pattern = re.compile(
        r'^\S+\(\d+\)\s+.+\s+\S+\(\d+\)\s*$'
    )

    lines = clean_text.splitlines()
    cleaned_lines = []
    blank_run = 0

    for line in lines:
        # Skip header/footer lines entirely
        if header_footer_pattern.match(line):
            continue

        # Strip leading indentation (page-level whitespace — not semantic)
        # and normalize internal multiple spaces to a single space
        stripped = re.sub(r' {2,}', ' ', line.lstrip())

        # Collapse runs of blank lines: allow at most 1 consecutive blank line
        if stripped == "":
            blank_run += 1
            if blank_run <= 1:
                cleaned_lines.append("")
        else:
            blank_run = 0
            cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines).strip()

def get_man_pages_in_section(section: str) -> list[str]:
    """
    Finds all available man pages for a given section by scanning standard directories.
    
    This acts as the "Scout" in the RAG ingestion pipeline. It does not read file contents;
    it simply walks the standard Linux man paths (/usr/share/man/ and /usr/local/share/man/)
    to determine which commands are installed and available for indexing. It strips the 
    file extensions (e.g., 'dmesg.8.gz' -> 'dmesg') and deduplicates the results.

    Args:
        section (str): The manual section to scan (e.g., "8").

    Returns:
        list[str]: A sorted list of command names available in that section.
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
