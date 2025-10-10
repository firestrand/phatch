#!/usr/bin/env python
"""Fix Python 2 PIL imports to Python 3 Pillow imports in action files.

This script converts old-style PIL imports to modern Pillow imports.
Following SOLID, DRY, KISS principles.

Example:
    import Image          → from PIL import Image
    import ImageOps       → from PIL import ImageOps
    import ImageChops     → from PIL import ImageChops

Usage:
    python fix_pil_imports.py --dry-run  # Preview changes
    python fix_pil_imports.py            # Apply changes
"""

import argparse
import re
import sys
from pathlib import Path


# Define PIL module import patterns
PIL_MODULES = [
    'Image',
    'ImageChops',
    'ImageColor',
    'ImageDraw',
    'ImageEnhance',
    'ImageFile',
    'ImageFilter',
    'ImageFont',
    'ImageGrab',
    'ImageMath',
    'ImageOps',
    'ImagePalette',
    'ImagePath',
    'ImageQt',
    'ImageSequence',
    'ImageStat',
    'ImageTk',
    'ImageWin',
]


def find_old_imports(content):
    """Find all old-style PIL imports in content.

    Args:
        content: File content as string

    Returns:
        List of tuples (line_number, old_import, module_name)
    """
    imports = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Match patterns like "    import Image" or "    import ImageOps"
        match = re.match(r'^(\s+)import\s+(Image\w*)$', line)
        if match:
            indent = match.group(1)
            module = match.group(2)
            if module in PIL_MODULES:
                imports.append((i, line, module, indent))

    return imports


def group_consecutive_imports(imports):
    """Group consecutive PIL imports that can be combined.

    Args:
        imports: List of (line_num, line, module, indent) tuples

    Returns:
        List of groups, where each group is a list of import tuples
    """
    if not imports:
        return []

    groups = []
    current_group = [imports[0]]

    for i in range(1, len(imports)):
        prev_line_num = imports[i-1][0]
        curr_line_num = imports[i][0]
        prev_indent = imports[i-1][3]
        curr_indent = imports[i][3]

        # Group if consecutive lines with same indentation
        if curr_line_num == prev_line_num + 1 and prev_indent == curr_indent:
            current_group.append(imports[i])
        else:
            groups.append(current_group)
            current_group = [imports[i]]

    groups.append(current_group)
    return groups


def generate_new_import(group):
    """Generate new from PIL import statement for a group.

    Args:
        group: List of import tuples from same location

    Returns:
        New import statement string
    """
    modules = [imp[2] for imp in group]
    indent = group[0][3]

    if len(modules) == 1:
        return f"{indent}from PIL import {modules[0]}"
    else:
        return f"{indent}from PIL import {', '.join(sorted(modules))}"


def fix_pil_imports(content):
    """Fix all PIL imports in content.

    Args:
        content: File content as string

    Returns:
        Tuple of (fixed_content, number_of_changes)
    """
    imports = find_old_imports(content)

    if not imports:
        return content, 0

    groups = group_consecutive_imports(imports)

    # Process groups in reverse order to maintain line numbers
    lines = content.split('\n')
    changes = 0

    for group in reversed(groups):
        # Get line range for this group (0-indexed)
        start_line = group[0][0] - 1
        end_line = group[-1][0] - 1

        # Replace the group with new import
        new_import = generate_new_import(group)

        # Remove old lines and insert new one
        del lines[start_line:end_line + 1]
        lines.insert(start_line, new_import)

        changes += len(group)

    return '\n'.join(lines), changes


def process_file(filepath, dry_run=False):
    """Process a single file to fix PIL imports.

    Args:
        filepath: Path to file to process
        dry_run: If True, only show changes without modifying

    Returns:
        Tuple of (success, num_changes, message)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, 0, f"Error reading file: {e}"

    new_content, num_changes = fix_pil_imports(content)

    if num_changes == 0:
        return True, 0, "No changes needed"

    if dry_run:
        return True, num_changes, f"Would fix {num_changes} import(s)"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True, num_changes, f"Fixed {num_changes} import(s)"
    except Exception as e:
        return False, 0, f"Error writing file: {e}"


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Fix Python 2 PIL imports to Python 3 Pillow imports'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--path',
        default='../../../phatch/actions',
        help='Path to actions directory (default: ../../../phatch/actions)'
    )

    args = parser.parse_args()

    # Get absolute path to actions directory
    script_dir = Path(__file__).parent
    actions_dir = (script_dir / args.path).resolve()

    if not actions_dir.exists():
        print(f"Error: Actions directory not found: {actions_dir}")
        sys.exit(1)

    print(f"Processing action files in: {actions_dir}")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")
    else:
        print("LIVE MODE - Files will be modified\n")

    # Find all Python files
    python_files = sorted(actions_dir.glob('*.py'))

    if not python_files:
        print("No Python files found")
        sys.exit(1)

    total_files = 0
    total_changes = 0
    files_modified = 0
    errors = []

    for filepath in python_files:
        if filepath.name == '__init__.py':
            continue

        success, num_changes, message = process_file(filepath, args.dry_run)

        if num_changes > 0:
            print(f"{'[DRY RUN] ' if args.dry_run else ''}✓ {filepath.name}: {message}")
            files_modified += 1
            total_changes += num_changes
        elif not success:
            print(f"✗ {filepath.name}: {message}")
            errors.append((filepath.name, message))

        total_files += 1

    print(f"\n{'=' * 60}")
    print("Summary:")
    print(f"  Total files processed: {total_files}")
    print(f"  Files {'that would be ' if args.dry_run else ''}modified: {files_modified}")
    print(f"  Total imports {'that would be ' if args.dry_run else ''}fixed: {total_changes}")

    if errors:
        print(f"  Errors: {len(errors)}")
        for filename, error in errors:
            print(f"    - {filename}: {error}")
        sys.exit(1)

    if args.dry_run and files_modified > 0:
        print("\nRun without --dry-run to apply these changes")
    elif files_modified > 0:
        print(f"\n✓ Successfully fixed PIL imports in {files_modified} files")
    else:
        print("\n✓ All files already use correct PIL imports")

    sys.exit(0)


if __name__ == '__main__':
    main()
