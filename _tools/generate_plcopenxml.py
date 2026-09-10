"""Generate CODESYS-importable PLCOpenXML directly from plaintext exports."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


PLCOPEN = "http://www.plcopen.org/xml/tc6_0200"
XHTML = "http://www.w3.org/1999/xhtml"
CODESYS = "http://www.3s-software.com/plcopenxml/"
UUID_NAMESPACE = uuid.UUID("38373369-c675-56f2-9c86-773b89f07a85")
TOP_LEVEL = re.compile(
    r"^(?P<prefix>POU|DUT|GVL|GVLP|I)\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)\.DEC\.exp$",
    re.IGNORECASE,
)
MEMBER = re.compile(
    r"^(?P<prefix>M|A|P)\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)\.DEC\.exp$",
    re.IGNORECASE,
)
ELEMENTARY = {
    "BOOL", "BYTE", "WORD", "DWORD", "LWORD", "SINT", "INT", "DINT", "LINT",
    "USINT", "UINT", "UDINT", "ULINT", "REAL", "LREAL", "TIME", "DATE", "DT", "TOD",
    "ANY", "ANY_DERIVED", "ANY_ELEMENTARY", "ANY_MAGNITUDE", "ANY_NUM", "ANY_REAL",
    "ANY_INT", "ANY_BIT", "ANY_STRING", "ANY_DATE",
}
VAR_SCOPES = {
    "VAR": "localVars",
    "VAR_TEMP": "tempVars",
    "VAR_INPUT": "inputVars",
    "VAR_OUTPUT": "outputVars",
    "VAR_IN_OUT": "inOutVars",
    "VAR_EXTERNAL": "externalVars",
    "VAR_STAT": "globalVars",
    "VAR_GLOBAL": "globalVars",
}


def q(name: str) -> str:
    return f"{{{PLCOPEN}}}{name}"


@dataclass(frozen=True)
class Variable:
    name: str
    type_text: str
    initial: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class VarBlock:
    scope: str
    constant: bool
    retain: bool
    persistent: bool
    variables: tuple[Variable, ...]


@dataclass
class Member:
    prefix: str
    name: str
    declaration: str
    implementation: str | None
    source: Path
    object_id: str = ""


@dataclass
class ObjectExport:
    prefix: str
    name: str
    declaration: str
    implementation: str | None
    folders: tuple[str, ...]
    source: Path
    members: list[Member] = field(default_factory=list)
    object_id: str = ""


@dataclass(frozen=True)
class RootSpec:
    path: Path
    mount: tuple[str, ...]
    label: str
    excluded_objects: frozenset[str] = frozenset()


class GenerationError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GenerationError(f"{path}: not valid UTF-8: {exc}") from exc


def load_manifests(repo_root: Path) -> list[dict]:
    manifests: list[dict] = []
    by_name: dict[str, dict] = {}
    for path in sorted(repo_root.glob("PlaintextExport/_lib_*/library.manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GenerationError(f"Invalid manifest {path}: {exc}") from exc
        name = manifest.get("name")
        if not isinstance(name, str) or not name:
            raise GenerationError(f"Manifest has no valid name: {path}")
        if name.casefold() in by_name:
            raise GenerationError(f"Duplicate library name: {name}")
        if not isinstance(manifest.get("dependencies"), dict):
            raise GenerationError(f"{name}: dependencies must be an object")
        for key in ("sourceRoots", "testRoots"):
            values = manifest.get(key)
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise GenerationError(f"{name}: {key} must be a list of paths")
        manifest["_path"] = path
        manifests.append(manifest)
        by_name[name.casefold()] = manifest
    for manifest in manifests:
        for dependency in manifest["dependencies"]:
            if dependency.casefold() not in by_name:
                raise GenerationError(f"{manifest['name']}: unknown dependency {dependency}")
    return manifests


def select_manifests(
    manifests: list[dict], selected: list[str], resolve_dependencies: bool
) -> tuple[list[dict], list[str]]:
    by_name = {manifest["name"].casefold(): manifest for manifest in manifests}
    requested: list[str] = []
    for name in selected:
        manifest = by_name.get(name.casefold())
        if manifest is None:
            raise GenerationError(f"Unknown library: {name}")
        if manifest["name"] not in requested:
            requested.append(manifest["name"])

    included = set(requested)
    if resolve_dependencies:
        def add_dependencies(name: str) -> None:
            for dependency in sorted(by_name[name.casefold()]["dependencies"]):
                canonical = by_name[dependency.casefold()]["name"]
                if canonical not in included:
                    included.add(canonical)
                    add_dependencies(canonical)

        for name in requested:
            add_dependencies(name)

    ordered: list[dict] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name not in included:
            return
        if name in visiting:
            raise GenerationError("Dependency cycle: " + " -> ".join(visiting + [name]))
        visiting.append(name)
        for dependency in sorted(by_name[name.casefold()]["dependencies"]):
            visit(by_name[dependency.casefold()]["name"])
        visiting.pop()
        visited.add(name)
        ordered.append(by_name[name.casefold()])

    for name in requested:
        visit(name)
    for name in sorted(included):
        visit(name)
    return ordered, [manifest["name"] for manifest in ordered if manifest["name"] not in requested]


def resolve_root(manifest: dict, relative: str) -> Path:
    library_root = manifest["_path"].parent.resolve()
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise GenerationError(f"{manifest['name']}: absolute root {relative}")
    root = (library_root / relative_path).resolve()
    if root != library_root and library_root not in root.parents:
        raise GenerationError(f"{manifest['name']}: root escapes library: {relative}")
    if not root.is_dir():
        raise GenerationError(f"{manifest['name']}: missing root {root}")
    return root


def build_root_specs(
    repo_root: Path, manifests: list[dict], test_library_names: set[str],
    include_shared_tests: bool, canonical_all: bool = False,
) -> list[RootSpec]:
    result: list[RootSpec] = []
    seen: list[tuple[Path, str]] = []

    def add(path: Path, mount: tuple[str, ...], label: str,
            excluded_objects: frozenset[str] = frozenset()) -> None:
        for previous, previous_label in seen:
            if path == previous or path in previous.parents or previous in path.parents:
                raise GenerationError(
                    f"Overlapping roots: {previous} ({previous_label}) and {path} ({label})"
                )
        seen.append((path, label))
        result.append(RootSpec(path, mount, label, excluded_objects))

    for manifest in manifests:
        excluded_objects = frozenset(
            item.casefold() for item in manifest.get("canonicalAllExcludeObjects", [])
        ) if canonical_all else frozenset()
        for relative in manifest["sourceRoots"]:
            add(resolve_root(manifest, relative), (), f"{manifest['name']} source",
                excluded_objects)
    if test_library_names:
        for manifest in manifests:
            if manifest["name"] not in test_library_names:
                continue
            excluded_objects = frozenset(
                item.casefold() for item in manifest.get("canonicalAllExcludeObjects", [])
            ) if canonical_all else frozenset()
            for relative in manifest["testRoots"]:
                add(resolve_root(manifest, relative), ("Tests",), f"{manifest['name']} tests",
                    excluded_objects)
    if include_shared_tests:
        shared = (repo_root / "PlaintextExport" / "Tests").resolve()
        if shared.is_dir() and not any(shared == root or shared in root.parents or root in shared.parents
                                       for root, _ in seen):
            add(shared, ("Tests",), "shared tests")
    return result


def _clean_declaration(text: str) -> str:
    """Remove comments and pragmas while preserving strings, lines, and token positions."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    block_depth = 0
    line_comment = False
    pragma = False
    while index < len(text):
        char = text[index]
        pair = text[index:index + 2]
        if line_comment:
            if char in "\r\n":
                line_comment = False
                output.append(char)
            else:
                output.append(" ")
        elif block_depth:
            if pair == "(*":
                block_depth += 1
                output.extend("  ")
                index += 1
            elif pair == "*)":
                block_depth -= 1
                output.extend("  ")
                index += 1
            else:
                output.append(char if char in "\r\n" else " ")
        elif pragma:
            if char == "}":
                pragma = False
            output.append(char if char in "\r\n" else " ")
        elif quote:
            output.append(char)
            if char == "$" and index + 1 < len(text):
                index += 1
                output.append(text[index])
            elif char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                    output.append(text[index])
                else:
                    quote = None
        elif pair == "//":
            line_comment = True
            output.extend("  ")
            index += 1
        elif pair == "(*":
            block_depth = 1
            output.extend("  ")
            index += 1
        elif char == "{":
            pragma = True
            output.append(" ")
        elif char in "'\"":
            quote = char
            output.append(char)
        else:
            output.append(char)
        index += 1
    if block_depth or quote or pragma:
        raise GenerationError("Unterminated comment, string, or pragma in declaration")
    return "".join(output)


def _split_top_level(text: str, separator: str) -> list[str]:
    result: list[str] = []
    start = 0
    round_depth = 0
    square_depth = 0
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "$":
                index += 1
            elif char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif char in "'\"":
            quote = char
        elif char == "(":
            round_depth += 1
        elif char == ")":
            round_depth = max(0, round_depth - 1)
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth = max(0, square_depth - 1)
        elif char == separator and round_depth == 0 and square_depth == 0:
            result.append(text[start:index])
            start = index + 1
        index += 1
    result.append(text[start:])
    return result


def _find_top_level(text: str, token: str) -> int:
    round_depth = 0
    square_depth = 0
    quote: str | None = None
    index = 0
    while index <= len(text) - len(token):
        char = text[index]
        if quote:
            if char == "$":
                index += 1
            elif char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 1
                else:
                    quote = None
        elif char in "'\"":
            quote = char
        elif char == "(":
            round_depth += 1
        elif char == ")":
            round_depth = max(0, round_depth - 1)
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth = max(0, square_depth - 1)
        elif round_depth == 0 and square_depth == 0 and text.startswith(token, index):
            return index
        index += 1
    return -1


def parse_variable(statement: str) -> tuple[Variable, ...]:
    statement = statement.strip()
    if not statement:
        return ()
    colon = _find_top_level(statement, ":")
    if colon < 0:
        raise GenerationError(f"Cannot parse variable declaration: {statement!r}")
    left = statement[:colon].strip()
    right = statement[colon + 1:].strip()
    initial_at = _find_top_level(right, ":=")
    if initial_at >= 0:
        type_text = right[:initial_at].strip()
        initial = right[initial_at + 2:].strip()
    else:
        ref_at = _find_top_level(right, "REF=")
        type_text = right[:ref_at].strip() if ref_at >= 0 else right
        initial = right[ref_at:].strip() if ref_at >= 0 else None
    address = None
    address_match = re.search(r"\s+AT\s+(.+)$", left, re.IGNORECASE)
    if address_match:
        address = address_match.group(1).strip()
        left = left[:address_match.start()].strip()
    names = [name.strip() for name in _split_top_level(left, ",") if name.strip()]
    if not names or not type_text:
        raise GenerationError(f"Cannot parse variable declaration: {statement!r}")
    for name in names:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise GenerationError(f"Unsupported variable name {name!r} in {statement!r}")
    return tuple(Variable(name, type_text, initial, address) for name in names)


def parse_var_blocks(declaration: str) -> tuple[VarBlock, ...]:
    cleaned = _clean_declaration(declaration)
    pattern = re.compile(
        r"(?im)^\s*(VAR(?:_(?:INPUT|OUTPUT|IN_OUT|TEMP|EXTERNAL|STAT|GLOBAL))?"
        r"(?:\s+(?:CONSTANT|RETAIN|PERSISTENT|NON_RETAIN))*)\s*$"
    )
    blocks: list[VarBlock] = []
    matches = list(pattern.finditer(cleaned))
    for match in matches:
        end_match = re.search(r"(?im)^\s*END_VAR\b", cleaned[match.end():])
        if end_match is None:
            raise GenerationError(f"Missing END_VAR after {match.group(1)}")
        body_end = match.end() + end_match.start()
        header = match.group(1).upper().split()
        scope = VAR_SCOPES.get(header[0])
        if scope is None:
            raise GenerationError(f"Unsupported variable scope: {header[0]}")
        variables: list[Variable] = []
        for statement in _split_top_level(cleaned[match.end():body_end], ";"):
            variables.extend(parse_variable(statement))
        blocks.append(VarBlock(
            scope=scope,
            constant="CONSTANT" in header,
            retain="RETAIN" in header and "NON_RETAIN" not in header,
            persistent="PERSISTENT" in header,
            variables=tuple(variables),
        ))
    return tuple(blocks)


def emit_type(parent: ET.Element, type_text: str) -> None:
    text = " ".join(type_text.split())
    array = re.fullmatch(r"ARRAY\s*\[(.*)]\s+OF\s+(.+)", text, re.IGNORECASE)
    if array:
        node = ET.SubElement(parent, q("array"))
        for dimension in _split_top_level(array.group(1), ","):
            bounds = dimension.split("..", 1)
            if len(bounds) != 2:
                bounds = ["0", "0"]
            ET.SubElement(node, q("dimension"), lower=bounds[0].strip(), upper=bounds[1].strip())
        base = ET.SubElement(node, q("baseType"))
        emit_type(base, array.group(2))
        return
    pointer = re.fullmatch(r"POINTER\s+TO\s+(.+)", text, re.IGNORECASE)
    if pointer:
        node = ET.SubElement(parent, q("pointer"))
        base = ET.SubElement(node, q("baseType"))
        emit_type(base, pointer.group(1))
        return
    string = re.fullmatch(r"(W?STRING)(?:\s*[\[(]\s*([^\])]+)\s*[\])])?", text, re.IGNORECASE)
    if string:
        attributes = {"length": string.group(2).strip()} if string.group(2) else {}
        ET.SubElement(parent, q("wstring" if string.group(1).upper() == "WSTRING" else "string"), attributes)
        return
    upper = text.upper()
    if upper in ELEMENTARY:
        ET.SubElement(parent, q(upper))
    else:
        ET.SubElement(parent, q("derived"), name=text)


def emit_variable(parent: ET.Element, variable: Variable) -> None:
    attributes = {"name": variable.name}
    if variable.address:
        attributes["address"] = variable.address
    node = ET.SubElement(parent, q("variable"), attributes)
    type_node = ET.SubElement(node, q("type"))
    emit_type(type_node, variable.type_text)
    if variable.initial:
        initial = ET.SubElement(node, q("initialValue"))
        ET.SubElement(initial, q("simpleValue"), value=variable.initial)


def emit_interface(parent: ET.Element, declaration: str) -> ET.Element:
    interface = ET.SubElement(parent, q("interface"))
    return_type = parse_return_type(declaration)
    if return_type:
        node = ET.SubElement(interface, q("returnType"))
        emit_type(node, return_type)
    for block in parse_var_blocks(declaration):
        attributes: dict[str, str] = {}
        if block.constant:
            attributes["constant"] = "true"
        if block.retain:
            attributes["retain"] = "true"
        if block.persistent:
            attributes["persistent"] = "true"
        var_list = ET.SubElement(interface, q(block.scope), attributes)
        for variable in block.variables:
            emit_variable(var_list, variable)
    inheritance = parse_pou_inheritance(declaration)
    if inheritance:
        add_data = ET.SubElement(interface, q("addData"))
        data = ET.SubElement(add_data, q("data"), {
            "name": CODESYS + "pouinheritance", "handleUnknown": "implementation",
        })
        node = ET.SubElement(data, q("Inheritance"))
        if inheritance[0]:
            ET.SubElement(node, q("Extends")).text = inheritance[0]
        for name in inheritance[1]:
            ET.SubElement(node, q("Implements")).text = name
    return interface


def parse_return_type(declaration: str) -> str | None:
    cleaned = _clean_declaration(declaration)
    match = re.search(
        r"(?im)^\s*(?:FUNCTION|METHOD)(?:\s+(?:PUBLIC|PRIVATE|PROTECTED|INTERNAL|FINAL|ABSTRACT))*"
        r"\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*([^\r\n]+)",
        cleaned,
    )
    return match.group(1).strip() if match else None


def parse_pou_kind(declaration: str) -> str:
    cleaned = _clean_declaration(declaration)
    match = re.search(r"(?im)^\s*(FUNCTION_BLOCK|FUNCTION|PROGRAM)\b", cleaned)
    if not match:
        raise GenerationError("POU declaration has no FUNCTION_BLOCK, FUNCTION, or PROGRAM header")
    return {"FUNCTION_BLOCK": "functionBlock", "FUNCTION": "function", "PROGRAM": "program"}[
        match.group(1).upper()
    ]


def parse_pou_inheritance(declaration: str) -> tuple[str | None, tuple[str, ...]] | None:
    cleaned = _clean_declaration(declaration)
    header = next((line.strip() for line in cleaned.splitlines()
                   if re.match(r"^(FUNCTION_BLOCK|FUNCTION|PROGRAM)\b", line.strip(), re.IGNORECASE)), "")
    if not header:
        return None
    extends = re.search(r"\bEXTENDS\s+([^\s]+)", header, re.IGNORECASE)
    implements = re.search(r"\bIMPLEMENTS\s+(.+)$", header, re.IGNORECASE)
    names = tuple(name.strip() for name in implements.group(1).split(",")) if implements else ()
    if not extends and not names:
        return None
    return (extends.group(1).strip() if extends else None, names)


def parse_interface_extends(declaration: str) -> str | None:
    cleaned = _clean_declaration(declaration)
    match = re.search(r"(?im)^\s*INTERFACE\s+\w+\s+EXTENDS\s+([^\s]+)", cleaned)
    return match.group(1).strip() if match else None


def plaintext_node(parent: ET.Element, declaration: str, wrapped: bool) -> None:
    if wrapped:
        add_data = parent.find(q("addData"))
        if add_data is None:
            add_data = ET.SubElement(parent, q("addData"))
        data = ET.SubElement(add_data, q("data"), {
            "name": CODESYS + "interfaceasplaintext", "handleUnknown": "implementation",
        })
        container = ET.SubElement(data, q("InterfaceAsPlainText"))
    else:
        container = ET.SubElement(parent, q("InterfaceAsPlainText"))
    ET.SubElement(container, "xhtml", xmlns=XHTML).text = declaration


def object_id_node(parent: ET.Element, object_id: str) -> None:
    add_data = parent.find(q("addData"))
    if add_data is None:
        add_data = ET.SubElement(parent, q("addData"))
    data = ET.SubElement(add_data, q("data"), {
        "name": CODESYS + "objectid", "handleUnknown": "discard",
    })
    ET.SubElement(data, q("ObjectId")).text = object_id


def body_node(parent: ET.Element, implementation: str | None) -> None:
    if implementation is None:
        return
    body = ET.SubElement(parent, q("body"))
    st = ET.SubElement(body, q("ST"))
    ET.SubElement(st, "xhtml", xmlns=XHTML).text = implementation


def emit_member(
    parent: ET.Element,
    member: Member,
    interface_method: bool,
    qualified_name: str | None = None,
) -> None:
    attributes = {"name": member.name, "ObjectId": member.object_id}
    if qualified_name:
        attributes["qualifiedName"] = qualified_name
    node = ET.SubElement(parent, q("Method"), attributes)
    emit_interface(node, member.declaration)
    if not interface_method:
        body_node(node, member.implementation or "")
    plaintext_node(node, member.declaration, wrapped=False)


def emit_pou(parent: ET.Element, obj: ObjectExport) -> None:
    node = ET.SubElement(parent, q("pou"), name=obj.name, pouType=parse_pou_kind(obj.declaration))
    emit_interface(node, obj.declaration)
    body_node(node, obj.implementation)
    if obj.members:
        add_data = ET.SubElement(node, q("addData"))
        for member in obj.members:
            data = ET.SubElement(add_data, q("data"), {
                "name": CODESYS + "method", "handleUnknown": "implementation",
            })
            emit_member(
                data, member, interface_method=False,
                qualified_name=f"{obj.name}.{member.name}",
            )
    plaintext_node(node, obj.declaration, wrapped=True)
    object_id_node(node, obj.object_id)


def _type_body(declaration: str) -> tuple[str, str]:
    cleaned = _clean_declaration(declaration)
    match = re.search(r"(?is)\bTYPE\s+\w+(?:\s+EXTENDS\s+[^:]+)?\s*:\s*(.*?)\s*END_TYPE\b", cleaned)
    if not match:
        raise GenerationError("DUT declaration has no TYPE ... END_TYPE body")
    body = match.group(1).strip()
    if re.match(r"^STRUCT\b", body, re.IGNORECASE):
        return "struct", re.sub(r"(?is)^STRUCT\b|\bEND_STRUCT\s*;?$", "", body).strip()
    if re.match(r"^UNION\b", body, re.IGNORECASE):
        return "union", re.sub(r"(?is)^UNION\b|\bEND_UNION\s*;?$", "", body).strip()
    if body.startswith("(") and re.search(r"\)\s*;?$", body):
        return "enum", re.sub(r"(?s)^\(|\)\s*;?$", "", body).strip()
    return "alias", body.rstrip(";").strip()


def emit_data_type(parent: ET.Element, obj: ObjectExport) -> None:
    kind, body = _type_body(obj.declaration)
    node = ET.SubElement(parent, q("dataType"), name=obj.name)
    base = ET.SubElement(node, q("baseType"))
    if kind == "struct":
        struct = ET.SubElement(base, q("struct"))
        for statement in _split_top_level(body, ";"):
            for variable in parse_variable(statement):
                emit_variable(struct, variable)
    elif kind == "enum":
        enum = ET.SubElement(base, q("enum"))
        values = ET.SubElement(enum, q("values"))
        for entry in _split_top_level(body, ","):
            entry = entry.strip()
            if not entry:
                continue
            assignment = _find_top_level(entry, ":=")
            attributes = {"name": entry[:assignment].strip() if assignment >= 0 else entry}
            if assignment >= 0:
                attributes["value"] = entry[assignment + 2:].strip()
            ET.SubElement(values, q("value"), attributes)
    else:
        emit_type(base, body)
    extends = re.search(r"(?im)^\s*TYPE\s+\w+\s+EXTENDS\s+([^\s:]+)", _clean_declaration(obj.declaration))
    if extends:
        add_data = ET.SubElement(node, q("addData"))
        data = ET.SubElement(add_data, q("data"), {
            "name": CODESYS + "datatypeinheritance", "handleUnknown": "implementation",
        })
        inheritance = ET.SubElement(data, q("Inheritance"))
        ET.SubElement(inheritance, q("Extends")).text = extends.group(1)
    plaintext_node(node, obj.declaration, wrapped=True)
    object_id_node(node, obj.object_id)


def emit_union(data: ET.Element, obj: ObjectExport) -> None:
    _, body = _type_body(obj.declaration)
    node = ET.SubElement(data, q("union"), name=obj.name)
    for statement in _split_top_level(body, ";"):
        for variable in parse_variable(statement):
            emit_variable(node, variable)
    plaintext_node(node, obj.declaration, wrapped=True)
    object_id_node(node, obj.object_id)


def emit_gvl(data: ET.Element, obj: ObjectExport) -> None:
    blocks = parse_var_blocks(obj.declaration)
    attributes = {"name": obj.name}
    if blocks and blocks[0].constant:
        attributes["constant"] = "true"
    if blocks and blocks[0].retain:
        attributes["retain"] = "true"
    if blocks and blocks[0].persistent:
        attributes["persistent"] = "true"
    node = ET.SubElement(data, q("globalVars"), attributes)
    for block in blocks:
        for variable in block.variables:
            emit_variable(node, variable)
    plaintext_node(node, obj.declaration, wrapped=True)
    object_id_node(node, obj.object_id)


def emit_codesys_interface(data: ET.Element, obj: ObjectExport) -> None:
    node = ET.SubElement(data, q("Interface"), name=obj.name, ObjectId=obj.object_id)
    if obj.members:
        methods = ET.SubElement(node, q("Methods"))
        for member in obj.members:
            emit_member(
                methods, member, interface_method=True,
                qualified_name=f"{obj.name}.{member.name}",
            )
    extends = parse_interface_extends(obj.declaration)
    if extends:
        inheritance = ET.SubElement(node, q("Inheritance"))
        ET.SubElement(inheritance, q("Extends")).text = extends
    plaintext_node(node, obj.declaration, wrapped=False)


def _signature(obj: ObjectExport) -> tuple:
    return (
        obj.declaration, obj.implementation,
        tuple((member.prefix, member.name, member.declaration, member.implementation)
              for member in obj.members),
    )


def discover_objects(specs: list[RootSpec]) -> list[ObjectExport]:
    objects: dict[tuple[str, str], ObjectExport] = {}
    origins: dict[tuple[str, str], str] = {}
    for spec in specs:
        for declaration_path in sorted(spec.path.rglob("*.DEC.exp")):
            relative = declaration_path.relative_to(spec.path)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts[:-1]):
                continue
            match = TOP_LEVEL.fullmatch(declaration_path.name)
            if not match:
                continue
            prefix = match.group("prefix").upper()
            name = match.group("name")
            if f"{prefix}.{name}".casefold() in spec.excluded_objects:
                continue
            implementation_path = declaration_path.with_name(
                declaration_path.name.replace(".DEC.exp", ".IMP.exp")
            )
            container = declaration_path.parent
            relative_folder = container.relative_to(spec.path)
            member_container = container.name.casefold() in {
                name.casefold(), f"pou.{name}".casefold()
            }
            if member_container:
                relative_folder = relative_folder.parent
            obj = ObjectExport(
                prefix=prefix,
                name=name,
                declaration=read_text(declaration_path),
                implementation=read_text(implementation_path) if implementation_path.is_file() else None,
                folders=spec.mount + relative_folder.parts,
                source=declaration_path,
            )
            if member_container:
                for member_path in sorted(container.glob("*.DEC.exp")):
                    member_match = MEMBER.fullmatch(member_path.name)
                    if not member_match:
                        continue
                    member_prefix = member_match.group("prefix").upper()
                    if member_prefix != "M":
                        raise GenerationError(
                            f"{member_path}: only method members are currently supported"
                        )
                    member_impl = member_path.with_name(member_path.name.replace(".DEC.exp", ".IMP.exp"))
                    obj.members.append(Member(
                        prefix=member_prefix,
                        name=member_match.group("name"),
                        declaration=read_text(member_path),
                        implementation=read_text(member_impl) if member_impl.is_file() else None,
                        source=member_path,
                    ))
            obj.members.sort(key=lambda member: member.name.casefold())
            key = (prefix.casefold(), name.casefold())
            if key in objects:
                if _signature(objects[key]) != _signature(obj):
                    raise GenerationError(
                        f"Divergent duplicate {prefix}.{name}: {origins[key]} and {spec.label}"
                    )
                continue
            objects[key] = obj
            origins[key] = spec.label

    for obj in objects.values():
        canonical = f"{obj.prefix}:{obj.name.casefold()}"
        obj.object_id = str(uuid.uuid5(UUID_NAMESPACE, canonical))
        for member in obj.members:
            member.object_id = str(uuid.uuid5(UUID_NAMESPACE, canonical + ":M:" + member.name.casefold()))
    return sorted(objects.values(), key=lambda obj: (
        tuple(part.casefold() for part in obj.folders), obj.name.casefold(), obj.prefix,
    ))


def read_object_list(path: Path) -> set[tuple[str, str]]:
    """Read strict PREFIX.Name identities for a targeted XML export."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GenerationError(f"Could not read object list {path}: {exc}") from exc

    requested: set[tuple[str, str]] = set()
    for line_number, line in enumerate(lines, 1):
        value = line.strip()
        if not value:
            continue
        match = re.fullmatch(r"(POU|DUT|GVL|GVLP|I)\.([A-Za-z_][A-Za-z0-9_]*)", value,
                            re.IGNORECASE)
        if match is None:
            raise GenerationError(
                f"{path}:{line_number}: expected top-level PREFIX.Name identity, got {value!r}"
            )
        requested.add((match.group(1).casefold(), match.group(2).casefold()))
    if not requested:
        raise GenerationError(f"Object list is empty: {path}")
    return requested


def filter_objects(
    objects: list[ObjectExport], requested: set[tuple[str, str]],
) -> list[ObjectExport]:
    """Keep the requested top-level objects and their members, or fail closed."""
    available = {(obj.prefix.casefold(), obj.name.casefold()): obj for obj in objects}
    missing = requested - set(available)
    if missing:
        names = ", ".join(
            f"{prefix.upper()}.{name}" for prefix, name in sorted(missing)
        )
        raise GenerationError(f"Object list requested unknown top-level object(s): {names}")
    return [obj for obj in objects
            if (obj.prefix.casefold(), obj.name.casefold()) in requested]


def project_structure(parent: ET.Element, objects: list[ObjectExport]) -> None:
    data = ET.SubElement(parent, q("data"), {
        "name": CODESYS + "projectstructure", "handleUnknown": "discard",
    })
    root = ET.SubElement(data, q("ProjectStructure"))
    folders: dict[tuple[str, ...], ET.Element] = {(): root}
    for obj in objects:
        path: tuple[str, ...] = ()
        for folder in obj.folders:
            next_path = path + (folder,)
            if next_path not in folders:
                folders[next_path] = ET.SubElement(folders[path], q("Folder"), Name=folder)
            path = next_path
        node = ET.SubElement(folders[path], q("Object"), Name=obj.name, ObjectId=obj.object_id)
        for member in obj.members:
            ET.SubElement(node, q("Object"), Name=member.name, ObjectId=member.object_id)


def build_xml(objects: list[ObjectExport], title: str) -> ET.ElementTree:
    ET.register_namespace("", PLCOPEN)
    root = ET.Element(q("project"))
    ET.SubElement(root, q("fileHeader"), {
        "companyName": "", "productName": "CODESYS",
        "productVersion": "CODESYS V3.5 SP22 Patch 2",
        "creationDateTime": "2000-01-01T00:00:00",
    })
    content = ET.SubElement(root, q("contentHeader"), {
        "name": title, "modificationDateTime": "2000-01-01T00:00:00",
    })
    coordinate = ET.SubElement(content, q("coordinateInfo"))
    for language in ("fbd", "ld", "sfc"):
        ET.SubElement(ET.SubElement(coordinate, q(language)), q("scaling"), x="1", y="1")

    types = ET.SubElement(root, q("types"))
    data_types = ET.SubElement(types, q("dataTypes"))
    pous = ET.SubElement(types, q("pous"))
    for obj in objects:
        if obj.prefix == "DUT":
            kind, _ = _type_body(obj.declaration)
            if kind != "union":
                emit_data_type(data_types, obj)
        elif obj.prefix == "POU":
            emit_pou(pous, obj)
    ET.SubElement(ET.SubElement(root, q("instances")), q("configurations"))

    add_data = ET.SubElement(root, q("addData"))
    for obj in objects:
        if obj.prefix in {"GVL", "GVLP"}:
            data = ET.SubElement(add_data, q("data"), {
                "name": CODESYS + "globalvars", "handleUnknown": "implementation",
            })
            emit_gvl(data, obj)
        elif obj.prefix == "I":
            data = ET.SubElement(add_data, q("data"), {
                "name": CODESYS + "interface", "handleUnknown": "implementation",
            })
            emit_codesys_interface(data, obj)
        elif obj.prefix == "DUT" and _type_body(obj.declaration)[0] == "union":
            data = ET.SubElement(add_data, q("data"), {
                "name": CODESYS + "union", "handleUnknown": "implementation",
            })
            emit_union(data, obj)
    project_structure(add_data, objects)
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def generate(
    repo_root: Path,
    library_names: list[str],
    output: Path,
    *,
    include_tests: bool = False,
    test_library_names: list[str] | None = None,
    resolve_dependencies: bool = True,
    object_list: Path | None = None,
    exclude_libraries: list[str] | None = None,
    canonical_all: bool = False,
) -> tuple[list[ObjectExport], list[str], list[str]]:
    manifests = load_manifests(repo_root)
    excluded = {name.casefold() for name in (exclude_libraries or [])}
    unknown_excluded = excluded - {manifest["name"].casefold() for manifest in manifests}
    if unknown_excluded:
        raise GenerationError(
            "Unknown excluded library: " + ", ".join(sorted(unknown_excluded))
        )
    requested_names = [name for name in library_names if name.casefold() not in excluded]
    selected, auto_added = select_manifests(manifests, requested_names, resolve_dependencies)
    auto_excluded = [name for name in auto_added if name.casefold() in excluded]
    if auto_excluded:
        raise GenerationError(
            "Excluded dependency required by selected library: " + ", ".join(sorted(auto_excluded))
        )
    selected = [manifest for manifest in selected if manifest["name"].casefold() not in excluded]
    auto_added = [name for name in auto_added if name.casefold() not in excluded]
    selected_names = {manifest["name"] for manifest in selected}
    selected_by_key = {name.casefold(): name for name in selected_names}
    requested_test_names = set(test_library_names or [])
    unknown_test_names = {
        name for name in requested_test_names if name.casefold() not in selected_by_key
    }
    if unknown_test_names:
        raise GenerationError(
            "Test libraries are not in the selected dependency closure: "
            + ", ".join(sorted(unknown_test_names))
        )
    test_names = selected_names if include_tests else {
        selected_by_key[name.casefold()] for name in requested_test_names
    }
    specs = build_root_specs(repo_root, selected, test_names, include_tests, canonical_all)
    objects = discover_objects(specs)
    if object_list is not None:
        objects = filter_objects(objects, read_object_list(object_list))
    title = "+".join(manifest["name"] for manifest in selected) + ".xml"
    output.parent.mkdir(parents=True, exist_ok=True)
    tree = build_xml(objects, title)
    tree.write(output, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
    return objects, [manifest["name"] for manifest in selected], auto_added


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("libraries", nargs="*", help="Manifest library names")
    result.add_argument("-o", "--output", type=Path, help="Output PLCOpenXML file")
    result.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    result.add_argument("--all", action="store_true", help="Generate all manifest libraries")
    result.add_argument("--include-tests", action="store_true", help="Include selected test roots")
    result.add_argument(
        "--test-library", action="append", default=[], metavar="NAME",
        help="Include tests for one selected library; may be repeated",
    )
    result.add_argument("--no-dependencies", action="store_true", help="Do not auto-add dependencies")
    result.add_argument(
        "--object-list", type=Path, metavar="PATH",
        help="Limit the XML to strict top-level PREFIX.Name identities in PATH",
    )
    result.add_argument(
        "--exclude-library", action="append", default=[], metavar="NAME",
        help="Explicitly exclude a manifest library; never resolves a divergent duplicate implicitly",
    )
    result.add_argument("--list", action="store_true", help="List available libraries and exit")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        manifests = load_manifests(repo_root)
        if args.list:
            for manifest in sorted(manifests, key=lambda item: item["name"].casefold()):
                print(manifest["name"])
            return 0
        if args.all and args.libraries:
            raise GenerationError("Use either --all or explicit library names, not both")
        effective_exclusions = list(args.exclude_library)
        excluded_names = {name.casefold() for name in effective_exclusions}
        names = ([manifest["name"] for manifest in manifests
                  if manifest["name"].casefold() not in excluded_names]
                 if args.all else args.libraries)
        if not names:
            raise GenerationError("Select one or more libraries, or use --all")
        if args.output is None:
            raise GenerationError("--output is required")
        objects, selected, auto_added = generate(
            repo_root, names, args.output.resolve(), include_tests=args.include_tests,
            test_library_names=args.test_library,
            resolve_dependencies=not args.no_dependencies,
            object_list=args.object_list.resolve() if args.object_list else None,
            exclude_libraries=effective_exclusions,
            canonical_all=args.all,
        )
    except (GenerationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Generated: {args.output.resolve()}")
    print(f"Libraries: {', '.join(selected)}")
    if auto_added:
        print(f"Dependencies added: {', '.join(auto_added)}")
    print(f"Objects: {len(objects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
