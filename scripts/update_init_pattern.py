#!/usr/bin/env python3
"""Script to update init() functions in action files to support dependency injection.

This script transforms lazy-loaded init() functions to support testing via
dependency injection while maintaining backward compatibility.

Before:
    def init():
        global Image
        from PIL import Image

After:
    def init(_inject_deps=None):
        '''Initialize action dependencies.

        Args:
            _inject_deps: For testing only. Dictionary of dependencies to inject.
                         If None, uses standard global imports.

        Returns:
            Dictionary of loaded dependencies (for testing verification)
        '''
        if _inject_deps:
            for name, value in _inject_deps.items():
                globals()[name] = value
            return _inject_deps

        # Production mode: standard lazy loading
        global Image
        from PIL import Image
        return {'Image': Image}
"""

import argparse
import re
import sys
from pathlib import Path


def extract_global_names(init_body):
    """Extract all global variable names from init() body."""
    global_pattern = re.compile(r'^\s*global\s+(.+)$', re.MULTILINE)
    names = []
    for match in global_pattern.finditer(init_body):
        # Handle "global foo, bar, baz" format
        names.extend(name.strip() for name in match.group(1).split(','))
    return names


def transform_init_function(content):
    """Transform init() function to support dependency injection."""
    # Pattern to match def init(): and capture only indented body lines
    lines = content.split('\n')
    init_start_idx = None
    init_end_idx = None
    function_indent = ''

    # Find init() function
    for i, line in enumerate(lines):
        if line.strip() == 'def init():':
            init_start_idx = i
            function_indent = line[:len(line) - len(line.lstrip())]
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                line_indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                if stripped and len(line_indent) <= len(function_indent):
                    init_end_idx = j
                    break
            if init_end_idx is None:
                init_end_idx = len(lines)
            break

    if init_start_idx is None:
        return None  # No init() function found

    # Extract the function body (only indented lines)
    init_body_lines = lines[init_start_idx + 1:init_end_idx]
    init_body = '\n'.join(init_body_lines)

    # Extract global names
    global_names = extract_global_names(init_body)
    if not global_names:
        return None  # No globals to refactor

    # Build the return statement
    return_dict = '{' + ', '.join(f"'{name}': {name}" for name in global_names) + '}'

    # Clean up the original body (remove blank lines and comments at start/end)
    clean_body_lines = []
    for line in init_body_lines:
        stripped = line.strip()
        # Keep all lines except pure comment lines
        if stripped and not (
                stripped.startswith('#')
                and 'lazily import' in stripped.lower()):
            clean_body_lines.append(line)

    # Build new init() function
    body_indent = function_indent + '    '
    new_init_lines = [
        function_indent + 'def init(_inject_deps=None):',
        body_indent + '"""Initialize action dependencies.',
        '',
        body_indent + 'Args:',
        body_indent
        + '    _inject_deps: For testing only. Dictionary of dependencies to inject.',
        body_indent + '                 If None, uses standard global imports.',
        '',
        body_indent + 'Returns:',
        body_indent
        + '    Dictionary of loaded dependencies (for testing verification)',
        body_indent + '"""',
        body_indent + 'if _inject_deps is not None:',
        body_indent + '    # Testing mode: inject mocked dependencies',
        body_indent + '    for name, value in _inject_deps.items():',
        body_indent + '        globals()[name] = value',
        body_indent + '    return _inject_deps',
        '',
        body_indent + '# Production mode: standard lazy loading',
    ]
    new_init_lines.extend(clean_body_lines)
    new_init_lines.append(f'{body_indent}return {return_dict}')

    # Reconstruct the file
    new_lines = lines[:init_start_idx] + new_init_lines + lines[init_end_idx:]
    return '\n'.join(new_lines)


def main(actions_dir):
    if not actions_dir.exists():
        print(f"Error: Actions directory not found: {actions_dir}", file=sys.stderr)
        return 1

    updated_count = 0
    skipped_count = 0

    for action_file in sorted(actions_dir.glob('*.py')):
        if action_file.name in ['__init__.py', 'common.py']:
            continue

        content = action_file.read_text(encoding='utf-8')

        # Skip if already transformed (check for _inject_deps)
        if '_inject_deps' in content:
            print(f"⏭️  Skipping (already updated): {action_file.name}")
            skipped_count += 1
            continue

        new_content = transform_init_function(content)

        if new_content:
            action_file.write_text(new_content, encoding='utf-8')
            print(f"✓ Updated: {action_file.name}")
            updated_count += 1
        else:
            print(f"⏭️  Skipping (no init() with globals): {action_file.name}")
            skipped_count += 1

    print(f"\nSummary: {updated_count} updated, {skipped_count} skipped")
    return 0


def parse_actions_dir():
    parser = argparse.ArgumentParser(
        description='Update legacy action init functions in an explicit directory.')
    parser.add_argument('actions_dir', type=Path)
    return parser.parse_args().actions_dir


if __name__ == '__main__':
    sys.exit(main(parse_actions_dir()))
