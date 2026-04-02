import pytest
from sysagent.rag.extractor import extract_man_text, get_man_pages_in_section


def test_extract_returns_nonempty_string():
    """
    Validates that calling man -Tutf8 on a known command returns content.
    ls(1) is available on every Linux system without exception.
    """
    result = extract_man_text("ls", "1")
    assert isinstance(result, str)
    assert len(result) > 0


def test_extract_has_no_terminal_formatting():
    """
    Validates that the regex cleanup removes backspace overstriking and ANSI codes.
    Backspace characters (\x08) are used for bold/underline in raw groff output.
    ANSI escape codes (\x1b) are used for color in some terminal-rendered man pages.
    Uses ls(1) which is universally available.
    """
    result = extract_man_text("ls", "1")
    assert "\x08" not in result, "Backspace overstriking was not stripped"
    assert "\x1b" not in result, "ANSI escape codes were not stripped"


def test_extract_contains_expected_content():
    """
    Validates that the extracted content meaningfully represents the man page.
    We check for the word 'ls' appearing in the ls(1) man page output.
    """
    result = extract_man_text("ls", "1")
    assert "ls" in result.lower()


def test_get_man_pages_in_section_returns_list():
    """
    Validates that the directory scanner finds man pages for section 8.
    """
    result = get_man_pages_in_section("8")
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_man_pages_in_section_contains_known_command():
    """
    Validates that mount(8) — a standard admin tool present on all Debian/Ubuntu systems
    is found in section 8. Note: dmesg appears in section 1 on Ubuntu/Debian,
    NOT section 8 (distro-specific packaging decision by util-linux maintainers).
    """
    result = get_man_pages_in_section("8")
    assert "mount" in result


def test_extract_raises_on_invalid_command():
    """
    Validates that passing a made-up command name raises a ValueError gracefully,
    rather than crashing the process or returning empty/garbage output.
    """
    with pytest.raises(ValueError):
        extract_man_text("this_command_does_not_exist_xyz", "1")
