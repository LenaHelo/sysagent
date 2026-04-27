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

    # Section headers are ALL CAPS lines (e.g. NAME, SYNOPSIS, OPTIONS).
    # We use this to: (1) truncate low-value tail sections, and (2) control blank lines.
    section_header_pattern = re.compile(r'^[A-Z][A-Z\s]+$')

    # These sections appear at the end of man pages and carry no diagnostic value.
    # We truncate the entire document when we encounter the first of these headers.
    low_value_sections = {"SEE ALSO", "AUTHOR", "AUTHORS", "REPORTING BUGS", "COPYRIGHT"}

    lines = clean_text.splitlines()
    cleaned_lines = []

    for line in lines:
        # Skip decorative header/footer lines entirely
        if header_footer_pattern.match(line):
            continue

        # Strip leading indentation and normalize internal multi-spaces
        stripped = re.sub(r' {2,}', ' ', line.lstrip())

        # Truncate at the first low-value section header
        if stripped in low_value_sections:
            break

        # Section-aware blank line handling:
        # - Before a section header: emit a double newline (\n\n) as a strong split signal
        # - All other blank lines within the body: drop them (collapse to nothing)
        #   so flags/entries flow as a dense block — the splitter uses \n\n as its
        #   primary boundary, keeping section content together in one chunk.
        if section_header_pattern.match(stripped):
            # Ensure previous content is separated from this header by a blank line
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            cleaned_lines.append(stripped)
        elif stripped == "":
            # Drop intra-section blank lines — they add no semantic value
            pass
        else:
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

# --- Kernel Docs RST Parser (docutils) ---
from pathlib import Path
from docutils.core import publish_doctree
from docutils import nodes
from docutils.parsers.rst import Directive, directives, roles

class DropDirective(Directive):
    """Ignores the directive and drops all its content."""
    has_content = True
    required_arguments = 0
    optional_arguments = 10
    final_argument_whitespace = True
    option_spec = {k: lambda x: x for k in ["maxdepth", "glob", "hidden", "caption", "name", "class", "alt", "align", "width", "height", "scale", "language", "linenos"]}
    def run(self):
        return []

class PassThroughDirective(Directive):
    """Ignores the directive label but parses its content as normal text."""
    has_content = True
    required_arguments = 0
    optional_arguments = 10
    final_argument_whitespace = True
    def run(self):
        if not self.content:
            return []
        node = nodes.container()
        self.state.nested_parse(self.content, self.content_offset, node)
        return node.children

# Register explicitly DROP directives
for name in [
    "include", "kernel-include", "maintainers-include", "literalinclude", 
    "kernel-doc", "kernel-abi", "kernel-feat", "automodule",
    "toctree", "contents", "sectnum", "c:namespace", "c:namespace-push", "c:namespace-pop", "ifconfig",
    "cssclass", "tabularcolumns", "raw", "highlight", "kernel-figure", "kernel-render"
]:
    directives.register_directive(name, DropDirective)

# Register explicitly PASSTHROUGH directives
for name in [
    "c:function", "c:macro", "c:type", "c:struct", "c:enum",
    "only", "seealso", "flat-table", "class", "note:"
]:
    directives.register_directive(name, PassThroughDirective)

# --- GLOBAL FALLBACK FOR FUTURE UNKNOWN DIRECTIVES ---
original_directive_func = directives.directive

def fallback_directive(directive_name, language_module, document):
    func_or_class, msg = original_directive_func(directive_name, language_module, document)
    if func_or_class is None:
        # If it's a completely unknown future directive, default to PassThrough
        # to ensure we never drop valuable text inside it.
        return PassThroughDirective, []
    return func_or_class, msg

directives.directive = fallback_directive
# -----------------------------------------------------

class CleanTextVisitor(nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)
        self.chunks = []
        
    def visit_Text(self, node):
        self.chunks.append(node.astext())
        
    def depart_paragraph(self, node):
        self.chunks.append("\n\n")

    def visit_literal_block(self, node):
        self.chunks.append(f"```\n{node.astext()}\n```\n\n")
        raise nodes.SkipNode
        
    def visit_row(self, node): pass
    def depart_row(self, node): self.chunks.append("\n")
    def visit_entry(self, node): self.chunks.append(" | ")
    def visit_list_item(self, node): self.chunks.append("- ")

    def visit_title(self, node):
        self.chunks.append(f"\n# {node.astext()}\n\n")
        raise nodes.SkipNode

    def visit_system_message(self, node): raise nodes.SkipNode
        
    def visit_problematic(self, node):
        text = node.astext()
        m = re.search(r'`([^`]+)`', text)
        if m:
            self.chunks.append(m.group(1))
        else:
            self.chunks.append(text)
        raise nodes.SkipNode

    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass

def get_rst_files(docs_path: Path) -> list[Path]:
    if not docs_path or not docs_path.exists() or not docs_path.is_dir():
        return []
    
    IGNORED_DIRS = {
        "translations",
        "process",
        "maintainer",
        "doc-guide",
        "dev-tools",
        "sphinx",
        "sphinx-includes",
        "sphinx-static",
        "litmus-tests",
        "kbuild",
        "kernel-hacking"
    }
    
    # rglob finds all .rst files, but we want to exclude noisy directories
    # to avoid database bloat and search pollution.
    all_rst_files = docs_path.rglob("*.rst")
    filtered_files = [
        f for f in all_rst_files 
        if not any(d in f.parts for d in IGNORED_DIRS)
    ]
    return sorted(filtered_files)

def extract_rst_text(filepath: Path) -> str:
    try:
        raw_text = filepath.read_text(encoding="utf-8", errors="replace")
        settings = {'report_level': 5, 'halt_level': 5}
        document = publish_doctree(raw_text, settings_overrides=settings)
        visitor = CleanTextVisitor(document)
        document.walkabout(visitor)
        
        final_text = "".join(visitor.chunks)
        final_text = re.sub(r'\n{3,}', '\n\n', final_text)
        return final_text.strip()
    except Exception as e:
        print(f"Failed to parse {filepath}: {e}")
        return ""
