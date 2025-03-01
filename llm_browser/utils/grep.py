"""
Grep-like content filtering utilities.
"""

import re
from typing import List, Tuple


class GrepOptions:
    """Options for grep-like filtering."""

    def __init__(
        self,
        pattern: str = "",
        context_lines: int = 0,
        invert_match: bool = False,
        show_line_numbers: bool = False,
        whole_words: bool = False,
    ):
        """
        Initialize grep options.

        Args:
            pattern: Regex pattern to search for
            context_lines: Number of lines to show before and after matches
            invert_match: If True, show non-matching lines
            show_line_numbers: If True, show line numbers with results
            whole_words: If True, match whole words only
        """
        self.pattern = pattern
        self.context_lines = context_lines
        self.invert_match = invert_match
        self.show_line_numbers = show_line_numbers
        self.whole_words = whole_words

    def to_cli_flags(self) -> str:
        """
        Convert options to CLI-style flags.

        Returns:
            String of grep-style CLI flags
        """
        flags = []

        if self.context_lines > 0:
            flags.append(f"-C {self.context_lines}")
        if self.invert_match:
            flags.append("-v")
        if self.show_line_numbers:
            flags.append("-n")
        if self.whole_words:
            flags.append("-w")

        return " ".join(flags)


def grep_content(
    content: str,
    pattern: str,
    context_lines: int = 0,
    invert_match: bool = False,
    show_line_numbers: bool = False,
    whole_words: bool = False,
) -> str:
    """
    Filter content based on grep-like patterns with advanced options.

    Args:
        content: Text content to filter
        pattern: Regex pattern to search for
        context_lines: Number of lines to show before and after matches
        invert_match: If True, show non-matching lines
        show_line_numbers: If True, show line numbers with results
        whole_words: If True, match whole words only

    Returns:
        Filtered content as string
    """
    if not pattern:
        return content

    lines = content.split("\n")
    result_lines = []
    matched_indices = set()

    try:
        # Apply word boundary if whole_words is True
        if whole_words:
            pattern = rf"\b{pattern}\b"

        regex = re.compile(pattern, re.IGNORECASE)

        # Find all matching line indices
        for i, line in enumerate(lines):
            is_match = bool(regex.search(line))
            if (is_match and not invert_match) or (not is_match and invert_match):
                matched_indices.add(i)

        # Add context lines
        if context_lines > 0 and not invert_match:
            context_indices = set()
            for idx in matched_indices:
                for j in range(
                    max(0, idx - context_lines),
                    min(len(lines), idx + context_lines + 1),
                ):
                    context_indices.add(j)
            matched_indices = matched_indices.union(context_indices)

        # Sort indices and build result
        for i in sorted(matched_indices):
            prefix = ""
            if show_line_numbers:
                prefix = f"{i + 1}: "

            # Mark actual matching lines (not just context) with ">" if showing context
            if context_lines > 0 and i in matched_indices and not invert_match:
                # Check if this is a direct match or just context
                is_direct_match = bool(regex.search(lines[i]))
                if is_direct_match:
                    prefix = f"> {prefix}"
                else:
                    prefix = f"  {prefix}"

            result_lines.append(f"{prefix}{lines[i]}")

    except re.error:
        # Fall back to simple string search if regex fails
        for i, line in enumerate(lines):
            is_match = pattern.lower() in line.lower()
            if (is_match and not invert_match) or (not is_match and invert_match):
                prefix = f"{i + 1}: " if show_line_numbers else ""
                result_lines.append(f"{prefix}{line}")

    return (
        "\n".join(result_lines)
        if result_lines
        else "No content matching the pattern was found."
    )


def find_sections(content: str, pattern: str) -> List[Tuple[int, int]]:
    """
    Find sections in content that match a pattern.

    This is useful for identifying logical sections like paragraphs or headers
    that contain the pattern.

    Args:
        content: Text content to search
        pattern: Regex pattern to search for

    Returns:
        List of (start_line, end_line) tuples for matching sections
    """
    lines = content.split("\n")
    sections = []

    try:
        regex = re.compile(pattern, re.IGNORECASE)

        # Find header lines (assuming headers start with #)
        header_indices = [
            i
            for i, line in enumerate(lines)
            if line.startswith("#")
            or (
                i > 0
                and lines[i - 1].strip()
                and all(c == "=" for c in lines[i - 1].strip())
            )
        ]

        # Add the end of the document
        header_indices.append(len(lines))

        # Check each section for matches
        section_start = 0
        for section_end in header_indices:
            section_text = "\n".join(lines[section_start:section_end])
            if regex.search(section_text):
                sections.append((section_start, section_end - 1))
            section_start = section_end

    except re.error:
        # Fall back to simple string search
        section_text = "\n".join(lines)
        if pattern.lower() in section_text.lower():
            sections.append((0, len(lines) - 1))

    return sections


def highlight_matches(content: str, pattern: str) -> str:
    """
    Highlight matches of a pattern in content.

    Args:
        content: Text content to search
        pattern: Regex pattern to highlight

    Returns:
        Content with matches highlighted using markdown bold
    """
    try:
        regex = re.compile(f"({pattern})", re.IGNORECASE)
        return regex.sub(r"**\1**", content)
    except re.error:
        # Fall back to simple replacement if regex fails
        return content.replace(pattern, f"**{pattern}**")
