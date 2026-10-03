# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, data-only recipe parsing and structural validation."""

import ast
import io
import json
from pathlib import Path
import tokenize

MAX_RECIPE_BYTES = 1024 * 1024
MAX_NESTING = 64
MAX_TOKENS = 100000


class RecipeValidationError(ValueError):
    """An invalid recipe with an actionable document location."""

    def __init__(self, location: str, reason: str) -> None:
        self.location = location
        super().__init__(f'{location}: {reason}')


def _bound_structure(source: str) -> None:
    depth = 0
    try:
        for count, token in enumerate(
            tokenize.generate_tokens(io.StringIO(source).readline)
        ):
            if count >= MAX_TOKENS:
                raise RecipeValidationError('$', 'token limit exceeded')
            if token.type != tokenize.OP:
                continue
            if token.string in {'[', '{', '('}:
                depth += 1
                if depth > MAX_NESTING:
                    raise RecipeValidationError('$', 'nesting limit exceeded')
            elif token.string in {']', '}', ')'}:
                depth -= 1
    except (tokenize.TokenError, IndentationError) as exc:
        raise RecipeValidationError('$', 'invalid document syntax') from exc


def parse_recipe(source: str) -> dict[str, object]:
    """Accept JSON or legacy Python literals; never execute expressions."""
    if len(source.encode('utf-8')) > MAX_RECIPE_BYTES:
        raise RecipeValidationError('$', 'recipe size limit exceeded')
    _bound_structure(source)
    try:
        try:
            document = json.loads(source)
        except json.JSONDecodeError:
            document = ast.literal_eval(source)
    except (ValueError, SyntaxError, RecursionError) as exc:
        raise RecipeValidationError(
            '$', 'expected JSON or literal data'
        ) from exc
    if not isinstance(document, dict):
        raise RecipeValidationError('$', 'expected an object')
    if not all(isinstance(key, str) for key in document):
        raise RecipeValidationError('$', 'keys must be strings')
    if 'description' in document and not isinstance(
        document['description'], str
    ):
        raise RecipeValidationError('description', 'expected a string')
    if 'schema_version' in document:
        from phatch.services.action_schema_types import parse_action_list
        parse_action_list(source)
        return document
    version = document.get('format_version')
    if version is not None and str(version) not in {'1.0', '2.0'}:
        raise RecipeValidationError('format_version', 'unsupported version')
    legacy_version = document.get('version')
    if (
        version is None
        and legacy_version
        and (
            not isinstance(legacy_version, str)
            or not legacy_version.startswith(('0.2', '0.3'))
        )
    ):
        raise RecipeValidationError('version', 'unsupported legacy version')
    actions = document.get('actions')
    if not isinstance(actions, list) or len(actions) > 10000:
        raise RecipeValidationError(
            'actions', 'expected at most 10000 actions'
        )
    for index, action in enumerate(actions):
        location = f'actions[{index}]'
        if not isinstance(action, dict):
            raise RecipeValidationError(location, 'expected an object')
        label = action.get('label')
        if not isinstance(label, str) or not label or len(label) > 256:
            raise RecipeValidationError(location + '.label', 'invalid label')
        plugin_id = action.get('plugin_id')
        if plugin_id is not None and (
            not isinstance(plugin_id, str)
            or not plugin_id
            or len(plugin_id) > 256
        ):
            raise RecipeValidationError(location + '.plugin_id', 'invalid ID')
        fields = action.get('fields')
        if not isinstance(fields, dict) or len(fields) > 512:
            raise RecipeValidationError(location + '.fields', 'invalid fields')
        for key, value in fields.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise RecipeValidationError(
                    location + f'.fields.{key}',
                    'expected string key and value',
                )
    return document


def read_recipe_text(filename: Path | str) -> str:
    """Read bounded UTF-8 recipe text before either schema parser runs."""
    with Path(filename).open('rb') as stream:
        contents = stream.read(MAX_RECIPE_BYTES + 1)
    if len(contents) > MAX_RECIPE_BYTES:
        raise RecipeValidationError('$', 'recipe size limit exceeded')
    try:
        source = contents.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise RecipeValidationError('$', 'expected UTF-8 data') from exc
    _bound_structure(source)
    return source


def read_recipe(filename: Path | str) -> dict[str, object]:
    """Bound input before allocating or decoding an entire file."""
    return parse_recipe(read_recipe_text(filename))
