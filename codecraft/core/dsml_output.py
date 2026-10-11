"""Normalize captured DSML calls into the existing guarded tool protocol.

Only complete calls envelopes are accepted. No invocation is executed here;
ToolExecutor remains responsible for validation and permissions.
"""

import json
import re

MARKER = r"(?:\uff5c\uff5cDSML\uff5c\uff5c|\|\|DSML\|\|)"
TAG_PREFIX = re.compile(r"(</?)" + MARKER + r"\s+")
ATTR = re.compile(r'([A-Za-z_][A-Za-z0-9_-]*)="([^"<>]*)"')


def _attrs(raw):
    values = {}
    end = 0
    for match in ATTR.finditer(raw):
        if raw[end:match.start()].strip() or match[1] in values:
            raise ValueError("invalid or duplicate DSML attributes")
        values[match[1]] = match[2]
        end = match.end()
    if raw[end:].strip():
        raise ValueError("invalid DSML attributes")
    return values


def parse_dsml(raw):
    # Do not treat prose, incomplete calls, or a valid prefix followed by a
    # broken invocation as an executable batch.
    normalized = TAG_PREFIX.sub(r"\1", raw.strip())
    envelope = re.fullmatch(r"<calls>\s*(.*?)\s*</calls>", normalized, re.DOTALL)
    if not envelope:
        raise ValueError("DSML requires a complete calls envelope")
    body = envelope[1]
    tools = []
    end = 0
    for invocation in re.finditer(r"<invoke\b([^>]*)>(.*?)</invoke>", body, re.DOTALL):
        if body[end:invocation.start()].strip():
            raise ValueError("unexpected content in DSML calls")
        attrs = _attrs(invocation[1])
        if set(attrs) != {"name"} or not attrs["name"].strip():
            raise ValueError("DSML invoke requires a tool name")
        args = {}
        parameters = invocation[2]
        parameter_end = 0
        for parameter in re.finditer(r"<parameter\b([^>]*)>(.*?)</parameter>", parameters, re.DOTALL):
            if parameters[parameter_end:parameter.start()].strip():
                raise ValueError("unexpected content in DSML invocation")
            fields = _attrs(parameter[1])
            name = fields.get("name", "")
            is_string = fields.get("string")
            if set(fields) != {"name", "string"} or not name or name in args:
                raise ValueError("invalid or duplicate DSML parameter")
            if is_string == "true":
                args[name] = parameter[2]
            elif is_string == "false":
                try:
                    args[name] = json.loads(parameter[2])
                except json.JSONDecodeError as exc:
                    raise ValueError("DSML non-string parameter requires valid JSON") from exc
            else:
                raise ValueError("DSML parameter string must be true or false")
            parameter_end = parameter.end()
        if parameters[parameter_end:].strip():
            raise ValueError("incomplete DSML parameters")
        # The captured provider also emits the harness name/args payload
        # as two parameters instead of passing tool arguments directly.
        if "args" in args:
            if set(args) - {"name", "args"} or not isinstance(args["args"], dict):
                raise ValueError("DSML wrapped args must be an object")
            if "name" in args and args["name"] != attrs["name"]:
                raise ValueError("DSML wrapped tool name mismatch")
            args = args["args"]
        tools.append({"name": attrs["name"], "args": args})
        end = invocation.end()
    if body[end:].strip() or not tools:
        raise ValueError("empty or incomplete DSML calls")
    return tools
