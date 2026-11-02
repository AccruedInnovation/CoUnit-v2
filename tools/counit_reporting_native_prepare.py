from __future__ import print_function

from scriptengine import *
import io
import json
import os
import traceback
import xml.etree.ElementTree as ET


CANONICAL_ROOT = os.path.normcase(os.path.abspath(r'D:\Projects\CoUnit-v2'))
BUILD_CATEGORY = Guid('97f48d64-a2a3-4856-b640-75c046e37ea9')
STATIC_CATEGORY = Guid('220493a1-f49b-4416-9a3f-a545db707cbe')
PLCOPEN = '{http://www.plcopen.org/xml/tc6_0200}'
CODESYS = 'http://www.3s-software.com/plcopenxml/'
try:
    TEXT = unicode
except NameError:
    TEXT = str


def text(value):
    return TEXT(value)


def normalized(value):
    if value is None:
        return None
    return text(value).replace('\r\n', '\n').replace('\r', '\n')


def implementation_readback_matches(kind, expected, implementation_document_present, actual):
    expected_text = normalized(expected)
    actual_text = normalized(actual)
    if expected_text == actual_text:
        return True
    return (kind == 'POU' and implementation_document_present and
            expected_text == '\n' and actual_text == '')


def local_name(tag):
    return tag.rsplit('}', 1)[-1]


def local_children(node, name):
    return [child for child in list(node) if local_name(child.tag) == name]


def under(path, root):
    try:
        relative = os.path.relpath(path, root)
    except ValueError:
        return False
    return relative == os.curdir or not (relative == os.pardir or relative.startswith(os.pardir + os.sep))


def required_path(args, name, suffix):
    value = args.get(name)
    if not value:
        raise ValueError('Missing required path: ' + name)
    value = os.path.abspath(text(value))
    if not value.lower().endswith(suffix):
        raise ValueError(name + ' must end with ' + suffix)
    if under(value, CANONICAL_ROOT):
        raise ValueError(name + ' must be outside the canonical CoUnit tree')
    return value


def object_name(obj):
    try:
        return text(obj.get_name())
    except Exception:
        return text(obj)


class Reporter(ImportReporter):
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.skipped_names = []
        self.added_names = []
        self.replaced_names = []

    def error(self, message):
        self.errors.append(text(message))

    def warning(self, message):
        self.warnings.append(text(message))

    def resolve_conflict(self, obj):
        self.replaced_names.append(object_name(obj))
        return ConflictResolve.Replace

    def added(self, obj):
        self.added_names.append(object_name(obj))

    def replaced(self, obj):
        self.replaced_names.append(object_name(obj))

    def skipped(self, name):
        self.skipped_names.append(text(name))

    @property
    def aborting(self):
        return bool(self.errors or self.skipped_names)


def object_id(node):
    value = node.get('ObjectId')
    if value:
        return text(value)
    for child in node.iter():
        if local_name(child.tag) == 'ObjectId' and child.text:
            return text(child.text)
    return None


def plain_declaration(node):
    containers = local_children(node, 'InterfaceAsPlainText')
    for add_data in local_children(node, 'addData'):
        for data in local_children(add_data, 'data'):
            if text(data.get('name', '')) == CODESYS + 'interfaceasplaintext':
                containers.extend(local_children(data, 'InterfaceAsPlainText'))
    for container in containers:
        for child in local_children(container, 'xhtml'):
            return child.text or ''
    return None


def implementation(node):
    for body in local_children(node, 'body'):
        for st in local_children(body, 'ST'):
            for child in local_children(st, 'xhtml'):
                return child.text or ''
    return None


def expected_paths(root):
    structures = [node for node in root.iter() if local_name(node.tag) == 'ProjectStructure']
    if len(structures) != 1:
        raise ValueError('PLCOpenXML must contain one ProjectStructure')
    by_id = {}

    def walk_object(node, path):
        identity = node.get('ObjectId')
        if not identity or identity in by_id:
            raise ValueError('PLCOpenXML has a missing or duplicate project object id')
        by_id[text(identity)] = path
        for child in local_children(node, 'Object'):
            walk_object(child, path + [text(child.get('Name'))])

    def walk_folder(node, path):
        for child in list(node):
            kind = local_name(child.tag)
            if kind == 'Folder':
                walk_folder(child, path + [text(child.get('Name'))])
            elif kind == 'Object':
                walk_object(child, path + [text(child.get('Name'))])

    walk_folder(structures[0], [])
    return by_id


def definitions(root):
    path_by_id = expected_paths(root)
    result = {}

    def add(node, kind):
        identity = object_id(node)
        path = path_by_id.get(identity)
        if path is None:
            raise ValueError('PLCOpenXML object is absent from its project structure: ' + text(node.get('name', node.get('Name', ''))))
        key = tuple(part.lower() for part in path)
        declaration = plain_declaration(node)
        if declaration is None:
            raise ValueError('PLCOpenXML object has no plaintext declaration: ' + '/'.join(path))
        if key in result:
            raise ValueError('PLCOpenXML repeats an object definition: ' + '/'.join(path))
        result[key] = {
            'path': path,
            'kind': kind,
            'declaration': declaration,
            'implementation': implementation(node),
            'children': set(),
        }

    types = root.find(PLCOPEN + 'types')
    if types is None:
        raise ValueError('PLCOpenXML has no types section')
    pous = types.find(PLCOPEN + 'pous')
    if pous is not None:
        for node in local_children(pous, 'pou'):
            add(node, 'POU')
            parent_key = tuple(part.lower() for part in path_by_id[object_id(node)])
            for method in [child for child in node.iter() if local_name(child.tag) == 'Method']:
                add(method, 'METHOD')
                child_key = tuple(part.lower() for part in path_by_id[object_id(method)])
                if child_key[:-1] != parent_key:
                    raise ValueError('PLCOpenXML method is not nested under its POU')
                result[parent_key]['children'].add(child_key[-1])

    data_types = types.find(PLCOPEN + 'dataTypes')
    if data_types is not None:
        for node in local_children(data_types, 'dataType'):
            add(node, 'DUT')

    for data in [node for node in root.iter() if local_name(node.tag) == 'data']:
        name = text(data.get('name', ''))
        if name == CODESYS + 'globalvars':
            for node in local_children(data, 'globalVars'):
                add(node, 'GVL')
        elif name == CODESYS + 'interface':
            for node in local_children(data, 'Interface'):
                add(node, 'INTERFACE')
                parent_key = tuple(part.lower() for part in path_by_id[object_id(node)])
                for method in [child for child in node.iter() if local_name(child.tag) == 'Method']:
                    add(method, 'METHOD')
                    child_key = tuple(part.lower() for part in path_by_id[object_id(method)])
                    if child_key[:-1] != parent_key:
                        raise ValueError('PLCOpenXML method is not nested under its interface')
                    result[parent_key]['children'].add(child_key[-1])

    if len(result) != len(path_by_id):
        missing = sorted('/'.join(path) for identity, path in path_by_id.items()
                         if tuple(part.lower() for part in path) not in result)
        raise ValueError('PLCOpenXML project structure has unbound objects: ' + ', '.join(missing[:12]))
    return result


def tree_inventory(project):
    result = {}
    for obj in project.get_children(True):
        names = []
        current = obj
        while current is not None and current is not project:
            names.insert(0, object_name(current))
            current = current.parent
        if current is project:
            key = tuple(name.lower() for name in names)
            if key in result:
                raise ValueError('Project readback has duplicate object path: ' + '/'.join(names))
            result[key] = obj
    return result


def check_readback(project, expected):
    actual = tree_inventory(project)
    for key in sorted(expected):
        row = expected[key]
        obj = actual.get(key)
        if obj is None:
            raise ValueError('Imported object missing on readback: ' + '/'.join(row['path']))
        declaration_document = getattr(obj, 'textual_declaration', None)
        if declaration_document is None:
            raise ValueError('Imported object has no textual declaration: ' + '/'.join(row['path']))
        actual_declaration = text(declaration_document.text)
        if normalized(actual_declaration) != normalized(row['declaration']):
            raise ValueError('Declaration readback mismatch: ' + '/'.join(row['path']))
        implementation_document = getattr(obj, 'textual_implementation', None)
        actual_implementation = None if implementation_document is None else text(implementation_document.text)
        expected_implementation = row['implementation']
        if expected_implementation is None:
            if actual_implementation not in (None, ''):
                raise ValueError('Unexpected implementation readback: ' + '/'.join(row['path']))
        elif not implementation_readback_matches(
                row['kind'], expected_implementation,
                implementation_document is not None, actual_implementation):
            raise ValueError('Implementation readback mismatch: ' + '/'.join(row['path']))
        if row['kind'] in ('POU', 'INTERFACE'):
            child_names = sorted(object_name(child).lower() for child in obj.get_children(False))
            expected_names = sorted(row['children'])
            if child_names != expected_names:
                raise ValueError('Nested child readback mismatch: ' + '/'.join(row['path']))
    return {'status': 'PASS', 'object_count': len(expected), 'nested_method_count': sum(len(row['children']) for row in expected.values())}


def severity_name(value):
    return text(value).strip().lower().rsplit('.', 1)[-1].replace('_', '').replace(' ', '')


def classify_severity(value):
    severity = severity_name(value)
    classifications = {
        'error': 'ERROR', 'fatalerror': 'ERROR', 'warning': 'WARNING',
        'information': 'INFORMATION', 'text': 'INFORMATION',
    }
    return classifications.get(severity, 'UNKNOWN')


def message_snapshot(category):
    category_text = text(category)
    snapshot = {'category': category_text, 'messages': [], 'capture_errors': [],
                'enumeration_complete': False, 'enumerated_count': 0,
                'serialized_count': 0, 'rows_omitted_count': 0}
    try:
        messages = list(system.get_message_objects(category=category))
    except Exception as exc:
        snapshot['capture_errors'].append('message enumeration: ' + text(exc))
        return snapshot
    snapshot['enumeration_complete'] = True
    snapshot['enumerated_count'] = len(messages)
    for message in messages:
        row = {'category': category_text, 'severity': None, 'classification': 'UNKNOWN',
               'text': None, 'capture_errors': []}
        try:
            row['severity'] = text(message.severity)
            row['classification'] = classify_severity(row['severity'])
        except Exception as exc:
            row['capture_errors'].append('severity: ' + text(exc))
        try:
            row['text'] = text(message.text)
        except Exception as exc:
            row['capture_errors'].append('text: ' + text(exc))
        snapshot['capture_errors'].extend(row['capture_errors'])
        snapshot['messages'].append(row)
    snapshot['serialized_count'] = len(snapshot['messages'])
    return snapshot


def diagnostic_counts(snapshot):
    rows = snapshot['messages']
    errors = sum(1 for row in rows if row['classification'] == 'ERROR')
    warnings = sum(1 for row in rows if row['classification'] == 'WARNING')
    known = ('ERROR', 'WARNING', 'INFORMATION')
    unclassified = sum(1 for row in rows if row['classification'] not in known)
    return errors, warnings, unclassified


def diagnostic_evidence(snapshot, completion_text, scope):
    errors, warnings, unclassified = diagnostic_counts(snapshot)
    complete_message_seen = any(
        row['classification'] == 'INFORMATION' and
        severity_name(row['severity']) == 'text' and
        row['text'] == completion_text and not row['capture_errors']
        for row in snapshot['messages'])
    scope_verified = isinstance(scope, dict) and scope.get('verified') is True
    complete = (snapshot['enumeration_complete'] and
                snapshot['enumerated_count'] == snapshot['serialized_count'] and
                snapshot['rows_omitted_count'] == 0 and
                not snapshot['capture_errors'] and unclassified == 0 and
                complete_message_seen and scope_verified)
    if errors or warnings:
        status = 'FAIL'
    elif complete:
        status = 'PASS'
    else:
        status = 'NOT_VERIFIED'
    return {
        'status': status,
        'classification': 'VERIFIED' if complete else 'NOT_VERIFIED',
        'complete': bool(complete),
        'scope_verified': scope_verified,
        'scope': scope,
        'completion_text': completion_text,
        'completion_message_seen': complete_message_seen,
        'error_count': errors,
        'warning_count': warnings,
        'unclassified_count': unclassified,
        'enumeration_complete': snapshot['enumeration_complete'],
        'enumerated_count': snapshot['enumerated_count'],
        'serialized_count': snapshot['serialized_count'],
        'rows_omitted_count': snapshot['rows_omitted_count'],
        'capture_errors': snapshot['capture_errors'],
        'messages': snapshot['messages'],
    }


def installed_library_inventory():
    values = []
    for library in librarymanager.get_all_libraries():
        values.append((text(library.company), text(library.title), text(library.version)))
    return sorted(values)


def write_report(path, value):
    payload = text(json.dumps(value, indent=2)).encode('utf-8')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 384)
    try:
        os.write(descriptor, payload)
    finally:
        os.close(descriptor)


args = {}
report_path = None
result = {'ok': False, 'status': 'NOT_RUN'}
try:
    args = json.loads(mcp_input_json)
    project_path = required_path(args, 'project', '.library')
    xml_path = required_path(args, 'xml', '.xml')
    compiled_path = required_path(args, 'compiled_library', '.compiled-library')
    report_path = required_path(args, 'report', '.json')
    if not os.path.isfile(xml_path):
        raise ValueError('PLCOpenXML closure does not exist: ' + xml_path)
    for path, name in ((compiled_path, 'compiled_library'), (report_path, 'report')):
        if os.path.exists(path):
            raise ValueError(name + ' output already exists')
        if not os.path.isdir(os.path.dirname(path)):
            raise ValueError(name + ' output directory does not exist')
    if os.path.normcase(project_path) == os.path.normcase(compiled_path):
        raise ValueError('Project and compiled-library output paths must differ')
    expected_company = text(args.get('expected_company', ''))
    expected_title = text(args.get('expected_title', ''))
    if not expected_company or not expected_title:
        raise ValueError('expected_company and expected_title must be supplied')
    project = projects.primary
    if project is None or os.path.normcase(os.path.abspath(text(project.path))) != os.path.normcase(project_path):
        raise ValueError('The primary project does not match the explicitly selected disposable library copy')
    if under(project_path, CANONICAL_ROOT):
        raise ValueError('Refusing to modify the canonical CoUnit source tree')
    if not hasattr(project, 'save_as_compiled_library'):
        raise ValueError('This ScriptEngine project does not expose save_as_compiled_library')
    if not hasattr(project, 'check_all_pool_objects'):
        raise ValueError('This ScriptEngine project does not expose check_all_pool_objects')
    info = project.get_project_info()
    if text(info.company) != expected_company or text(info.title) != expected_title:
        raise ValueError('Disposable library identity does not match the requested company/title')
    version_before = text(info.version)
    if version_before not in ('2.0.0.0', '2.0.1.0'):
        raise ValueError('Expected source library version 2.0.0.0 or 2.0.1.0, found ' + version_before)
    installed_before = installed_library_inventory()
    xml_root = ET.parse(xml_path).getroot()
    expected = definitions(xml_root)
    result.update(project=project_path, xml=xml_path, compiled_library=compiled_path,
                  expected_source_version=version_before, target_version='2.0.1.0')

    reporter = Reporter()
    project.import_xml(dataOrPath=xml_path, reporter=reporter, import_folder_structure=True)
    result['import'] = {'added': reporter.added_names, 'replaced': reporter.replaced_names,
                        'warnings': reporter.warnings, 'errors': reporter.errors,
                        'skipped': reporter.skipped_names}
    if reporter.errors or reporter.warnings or reporter.skipped_names:
        raise ValueError('PLCOpenXML import reported warnings, errors, or skipped objects')

    project = projects.get_by_path(project_path)
    if project is None or projects.primary is None or os.path.normcase(os.path.abspath(text(projects.primary.path))) != os.path.normcase(project_path):
        raise ValueError('Primary project identity changed after import')
    result['readback'] = check_readback(project, expected)

    info = project.get_project_info()
    if bool(info.released):
        info.released = False
    info.version = '2.0.1.0'
    if text(info.version) != '2.0.1.0':
        raise ValueError('Project Information version readback mismatch')
    project.save()
    result['project_info'] = {'company': text(info.company), 'title': text(info.title),
                              'version': text(info.version), 'released': bool(info.released)}

    system.clear_messages(BUILD_CATEGORY)
    cleared_build = message_snapshot(BUILD_CATEGORY)
    if (not cleared_build['enumeration_complete'] or cleared_build['messages'] or
            cleared_build['capture_errors']):
        raise ValueError('Build category could not be freshly cleared and verified empty')
    project.check_all_pool_objects()
    build_scope = {'verified': True, 'project_path': project_path,
                   'operation': 'project.check_all_pool_objects'}
    build_before_analysis = diagnostic_evidence(
        message_snapshot(BUILD_CATEGORY), 'Compile complete -- 0 errors, 0 warnings', build_scope)
    result['build_before_analysis'] = build_before_analysis
    result['compiler'] = text(project.project_settings.get_compilerversion())
    if build_before_analysis['status'] != 'PASS':
        raise ValueError('Library pool compile is not affirmatively verified clean: ' + build_before_analysis['status'])

    system.clear_messages(STATIC_CATEGORY)
    cleared_analysis = message_snapshot(STATIC_CATEGORY)
    if (not cleared_analysis['enumeration_complete'] or cleared_analysis['messages'] or
            cleared_analysis['capture_errors']):
        raise ValueError('Static Analysis category could not be freshly cleared and verified empty')
    commands = [command for command in system.commands if text(command.name) == 'Run Static Analysis']
    if len(commands) != 1:
        raise ValueError('Expected exactly one Run Static Analysis command')
    execute_error = None
    try:
        # execute() returning is not completion evidence; the IDE completion row is required below.
        commands[0].execute()
    except Exception as exc:
        execute_error = text(exc)

    build_after_analysis_snapshot = message_snapshot(BUILD_CATEGORY)
    analysis_after_return_snapshot = message_snapshot(STATIC_CATEGORY)
    primary_after_analysis = projects.primary
    primary_matches = (primary_after_analysis is not None and
                       os.path.normcase(os.path.abspath(text(primary_after_analysis.path))) ==
                       os.path.normcase(project_path))
    analysis_scope = {'verified': execute_error is None and primary_matches,
                      'project_path': project_path,
                      'primary_project_matches': primary_matches,
                      'command': text(commands[0].name),
                      'category': text(STATIC_CATEGORY)}
    build_after_scope = {'verified': primary_matches,
                         'project_path': project_path,
                         'primary_project_matches': primary_matches,
                         'operation': 'project.check_all_pool_objects'}
    result['build'] = diagnostic_evidence(
        build_after_analysis_snapshot, 'Compile complete -- 0 errors, 0 warnings', build_after_scope)
    result['analysis'] = diagnostic_evidence(
        analysis_after_return_snapshot, 'Static analysis complete -- 0 errors, 0 warnings', analysis_scope)
    result['analysis']['execute_error'] = execute_error
    result['build']['compiler'] = text(project.project_settings.get_compilerversion())
    if result['build']['status'] != 'PASS':
        raise ValueError('Build diagnostics after Static Analysis are not affirmatively verified clean: ' + result['build']['status'])
    if result['analysis']['status'] != 'PASS':
        raise ValueError('Static Analysis is not affirmatively verified clean: ' + result['analysis']['status'])

    project.save_as_compiled_library(compiled_path)
    if not os.path.isfile(compiled_path) or os.path.getsize(compiled_path) <= 0:
        raise ValueError('CODESYS did not produce a nonempty compiled-library file')
    installed_after = installed_library_inventory()
    if installed_after != installed_before:
        raise ValueError('Installed library inventory changed during uninstalled export')
    result['export'] = {'status': 'SAVED_UNINSTALLED', 'path': compiled_path,
                        'size_bytes': os.path.getsize(compiled_path),
                        'installed_library_inventory_unchanged': True}
    result['ok'] = True
    result['status'] = 'PASS'
except Exception:
    result['exception'] = traceback.format_exc()
    result['status'] = 'FAIL'
finally:
    if report_path:
        try:
            write_report(report_path, result)
            result['report_written'] = True
        except Exception:
            result['report_write_exception'] = traceback.format_exc()
            result['ok'] = False
            result['status'] = 'FAIL'

mcp_result = json.dumps(result)
