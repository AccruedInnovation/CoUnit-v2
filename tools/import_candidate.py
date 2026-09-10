"""CODESYS ScriptEngine: update an isolated library from its explicit source root.

Invoke via MCP with JSON containing source, target and report absolute paths.
Keeps native library references/settings and every existing property accessor.
"""
from scriptengine import *
import io, json, os, re, traceback

args = json.loads(mcp_input_json)
source, target, report = [os.path.abspath(args[k]) for k in ('source', 'target', 'report')]
if not target.lower().endswith('.library') or '2.0.0' not in target:
    raise ValueError('Expected isolated 2.0.0 library target')
if os.path.normcase(target) == os.path.normcase(str(projects.primary.path)):
    raise ValueError('Candidate must be a non-primary library copy')
result = {'ok': False, 'source': source, 'target': target, 'created': [], 'sections': 0}

with io.open(os.path.join(args['tools'], 'sync_plaintext.py'), 'r', encoding='utf-8') as helper:
    exec(compile(helper.read(), helper.name, 'exec'))

try:
    try: candidate = projects.get_by_path(target)
    except SystemError: candidate = None
    if candidate is None: candidate = projects.open(target, primary=False)
    for name in args.get('recreate_objects', []):
        matches = list(candidate.find(name, True))
        if len(matches) != 1: raise ValueError('Expected one candidate object ' + name)
        parent = matches[0].parent
        matches[0].remove()
        parent.create_function_block(name, ImplementationLanguages.st)
    runners = list(candidate.find('FB_coUnitRunner', True))
    if len(runners) == 1 and not any(obj.get_name() == 'CheckViolation' for obj in runners[0].get_children(False)):
        parent = runners[0].parent
        runners[0].remove()
        parent.create_function_block('FB_coUnitRunner', ImplementationLanguages.st)
        result['recreated_legacy_runner'] = True
    sync(candidate, source)
    info = candidate.get_project_info()
    info.version = '2.0.0.0'
    result['version'] = str(info.version)
    candidate.save()
    result['ok'] = True
except Exception:
    result['exception'] = traceback.format_exc()
finally:
    with io.open(report, 'w', encoding='utf-8') as stream:
        stream.write(unicode(json.dumps(result, indent=2)))
mcp_result = json.dumps(result)
