"""Bounded ScriptEngine qualification in an explicitly named simulator copy."""
from scriptengine import *
import io, json, os, re, traceback
from System import DateTime

args = json.loads(mcp_input_json)
target = os.path.abspath(args['project'])
result = {'ok': False, 'project': target, 'messages': []}
if 'CoUnit2' not in target or not target.endswith('qualification.project'):
    raise ValueError('Expected isolated CoUnit2 qualification project')
original = str(projects.primary.path)
session = None
parameter_preimage = None
prompt_preimage = (system.script_prompt_handling, system.log_prompt_details)
prompt_keys = ('QueryProgramChanged', 'QueryCreateApplication', 'CleanActiveApplication_Query', 'CleanAll_Query')
prompt_answers = dict((key, system.prompt_answers[key]) for key in prompt_keys if key in system.prompt_answers)

class Reporter(ImportReporter):
    def __init__(self): self.errors = []
    def error(self, message): self.errors.append(str(message))
    def warning(self, message): pass
    def resolve_conflict(self, obj): return ConflictResolve.Replace
    def added(self, obj): pass
    def replaced(self, obj): pass
    def skipped(self, name): self.errors.append('Skipped ' + str(name))
    @property
    def aborting(self): return bool(self.errors)

types = set(['738bea1e-99bb-4f04-90bb-a7a567e74e3a',
    'ffbfa93a-b94d-45fc-a329-229860183b1d', '261bd6e6-249c-4232-bb6f-84c2fbeef430',
    '6f9dac99-8de1-4efc-8465-68ac443b7d08', '2db5746d-d284-4425-9f7f-2663a34b0ebc',
    '6654496c-404d-479a-aad2-8551054e5f1e'])

def clear(container):
    for child in list(container.get_children(False)):
        if str(child.type).lower() in types: child.remove()
        else: clear(child)

try:
    system.script_prompt_handling = ScriptPromptHandling.LogPrompts
    system.log_prompt_details = True
    for key in prompt_keys: system.prompt_answers[key] = PromptResult.Yes
    try: project = projects.get_by_path(target)
    except SystemError: project = None
    if project is None: project = projects.open(target, primary=False)
    if args.get('clear', True):
        for obj in list(project.get_children(False)):
            if obj.get_name() in ('Support', 'Unit Test Framework for CODESYS'): obj.remove()
        clear(project)
    else:
        for obj in list(project.get_children(False)):
            if obj.get_name() in ('Qualification', 'PRG_TEST'):
                obj.remove()
    applications = [obj for obj in project.find('Application', True)
                    if str(obj.type).lower() == '639b491f-5557-464c-af91-1471bac9f549']
    if len(applications) != 1: raise ValueError('Expected one application in simulator copy')
    application = applications[0]
    project.active_application = application
    if args.get('restore_log_dependency'):
        manager = project.get_library_manager()
        for reference in list(manager.references):
            if reference.name.startswith('CmpLog, 3.5.21.0 '): manager.remove_library(reference.name)
        if not any(r.name == '#CmpLog' for r in manager.references): manager.add_placeholder('CmpLog', 'CmpLog, * (System)')
    if 'log_extended_results' in args:
        parameter = next(iter(project.find('GVL_Param_coUnit', True)))
        parameter_preimage = (parameter.textual_declaration, parameter.textual_declaration.text)
        value = 'TRUE' if args['log_extended_results'] else 'FALSE'
        replacement, count = re.subn(r'(LogExtendedResults\s*:\s*BOOL\s*:=\s*)(TRUE|FALSE)', r'\g<1>' + value, parameter_preimage[1])
        if count != 1: raise ValueError('Expected exact verbosity parameter')
        parameter.textual_declaration.replace(new_text=replacement)
        result['log_extended_results'] = args['log_extended_results']
    if args.get('log_observer_library'):
        manager = project.get_library_manager()
        for r in list(manager.references):
            if r.name == '#CmpLog': manager.remove_library(r.name)
        if not any(r.name.startswith('CmpLog, 3.5.21.0 ') for r in manager.references):
            library = next(lib for lib in librarymanager.get_all_libraries() if lib.title == 'CmpLog' and str(lib.version) == '3.5.21.0')
            manager.add_library(library)
        reference = next(r for r in manager.references if r.name.startswith('CmpLog, 3.5.21.0 '))
        reference.namespace = 'CmpLog'
        reference.qualified_only = True
        result['log_library_bindings'] = [r.name + ' namespace=' + r.namespace for r in manager.references if r.name.split(',')[0] == 'CmpLog']
    for title in args.get('extra_libraries', []):
        manager = project.get_library_manager()
        if not any(r.name.split(',')[0] == title for r in manager.references):
            candidates = [lib for lib in librarymanager.get_all_libraries() if lib.title == title]
            if not candidates: raise ValueError('Missing qualification dependency ' + title)
            manager.add_library(sorted(candidates, key=lambda lib: lib.version)[-1])
        result.setdefault('qualification_libraries', []).append(str(next(r for r in manager.references if r.name.split(',')[0] == title)))
    if args.get('source'):
        for manager in (project.get_library_manager(), application.get_library_manager()):
            for entry in list(manager.get_libraries()):
                if 'counit' in str(entry).lower(): manager.remove_library(str(entry))
        if args.get('dependency_template'):
            template = projects.get_by_path(args['dependency_template'])
            manager = project.get_library_manager()
            for reference in template.get_library_manager().references:
                existing = [r for r in manager.references if r.name.split(',')[0] == reference.name.split(',')[0]]
                if not existing:
                    if reference.is_placeholder:
                        manager.add_placeholder(reference.placeholder_name, reference.default_resolution)
                    else: manager.add_library(reference.managed_library)
                copied = next(r for r in manager.references if r.name.split(',')[0] == reference.name.split(',')[0])
                copied.namespace = reference.namespace
                copied.qualified_only = reference.qualified_only
                copied.publish_symbols_in_container = reference.publish_symbols_in_container
        result['created'], result['sections'] = [], 0
        with io.open(os.path.join(args['tools'], 'sync_plaintext.py'), 'r', encoding='utf-8') as helper:
            exec(compile(helper.read(), helper.name, 'exec'))
        sync(project, args['source'])
    if args.get('library'):
        repositories = [repo for repo in librarymanager.repositories if repo.name == 'System']
        if len(repositories) != 1:
            raise RuntimeError('Expected exactly one System library repository')
        librarymanager.install_library(args['library'], repository=repositories[0], overwrite=True)
        manager = application.get_library_manager()
        for entry in list(manager.get_libraries()):
            if 'counit' in str(entry).lower(): manager.remove_library(str(entry))
        candidates = [lib for lib in librarymanager.get_all_libraries()
                      if lib.title == 'coUnit - A unittest framework for CODESYS' and str(lib.version) == '2.0.0.0']
        if len(candidates) != 1: raise ValueError('Expected exact installed CoUnit 2.0.0.0')
        manager.add_library(candidates[0])
        reference = next(r for r in manager.references if r.name.startswith('coUnit - A unittest framework for CODESYS, 2.0.0.0 '))
        reference.qualified_only = False
        result['libraries'] = [str(x) for x in manager.get_libraries()]
    for xml in args.get('xmls', [args['xml']] if args.get('xml') else []):
        reporter = Reporter()
        project.import_xml(dataOrPath=xml, reporter=reporter, import_folder_structure=True)
        if reporter.errors: raise ValueError('; '.join(reporter.errors))
    project = projects.get_by_path(target)
    application = next(obj for obj in project.find('Application', True)
                       if str(obj.type).lower() == '639b491f-5557-464c-af91-1471bac9f549')
    project.active_application = application
    for hook in args.get('test_hooks', []):
        owners = project.find(hook['owner'], True)
        if len(owners) != 1: raise ValueError('Ambiguous qualification hook owner')
        matches = owners[0].find(hook['name'], False)
        method = matches[0] if matches else owners[0].create_method(hook['name'])
        for kind, attribute in [('DEC', 'textual_declaration'), ('IMP', 'textual_implementation')]:
            with io.open(os.path.join(hook['directory'], hook['name'] + '.' + kind + '.exp'), encoding='utf-8') as stream:
                expected = stream.read()
            document = getattr(method, attribute)
            document.replace(new_text=expected)
            if document.text.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
                raise ValueError('Qualification hook read-back mismatch')
    if args.get('declaration'):
        program = project.create_program('PRG_TEST')
        program.textual_declaration.replace(new_text=args['declaration'])
        program.textual_implementation.replace(new_text=args['implementation'])
    else:
        program = project.create_program('PRG_TEST')
        initialization = ''
        if args.get('report_path'):
            if "'" in args['report_path']: raise ValueError('Unsupported quote in report path')
            initialization = "GVL_coUnit.xUnitFilePath := '" + args['report_path'].replace('\\', '/') + "';\n"
        initialization += args.get('fixture_inputs', '')
        program.textual_implementation.replace(new_text=initialization + 'PRG_Qualification();')
        if args.get('drain_completed'):
            program.textual_declaration.replace(new_text='PROGRAM PRG_TEST\nVAR\n _drain : UINT;\nEND_VAR')
            program.textual_implementation.replace(new_text=initialization +
                'PRG_Qualification();\nIF PRG_Qualification.Done THEN\n' +
                ' FOR _drain := 1 TO 32 DO RUN_IN_SEQUENCE(); END_FOR\nEND_IF')
    for method_files in args.get('runner_methods', []):
        method = program.create_method(method_files['name'])
        for key, attribute in [('declaration', 'textual_declaration'), ('implementation', 'textual_implementation')]:
            with io.open(method_files[key], encoding='utf-8-sig') as stream: expected = stream.read()
            document = getattr(method, attribute)
            document.replace(new_text=expected)
            if document.text.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
                raise ValueError('Runner method read-back mismatch')
    for task in list(application.get_children(True)):
        if task.is_task and task.get_name() == 'CoUnitQualificationForeign': task.remove()
    if args.get('foreign_task'):
        main = next(t for t in application.get_children(True) if t.is_task and t.get_name() == 'MainTask')
        configuration = main.parent
        foreign = configuration.create_task('CoUnitQualificationForeign')
        foreign.kind_of_task = KindOfTask.Cyclic
        foreign.interval, foreign.interval_unit = '2', 'ms'
        foreign.priority = '20'
        foreign.watchdog.enabled = False
        foreign.pous.add('PRG_QualificationForeign', 'CoUnit source qualification only')
    tasks = [t for t in application.get_children(True) if t.is_task]
    for task in tasks:
        if task.get_name() == 'MainTask':
            task.interval, task.interval_unit = '1', 'ms'
            task.watchdog.enabled = False
    result['tasks'] = [{'name':t.get_name(), 'calls':list(t.pous), 'interval':t.interval, 'unit':t.interval_unit} for t in tasks]
    category = Guid('97f48d64-a2a3-4856-b640-75c046e37ea9')
    if args.get('clean_all'):
        if str(projects.primary.path) != target: raise ValueError('Clean requires the isolated primary project')
        next(c for c in system.commands if str(c.guid) == '024a0dc9-987d-42be-add4-5775c60d128a').execute()
    system.clear_messages(category)
    project.active_application.build()
    for message in system.get_message_objects(category=category):
        row = {'severity': str(message.severity), 'text': unicode(message.text)}
        try: row['object'] = str(message.object.get_name()); row['position'] = str(message.position_text)
        except Exception: pass
        result['messages'].append(row)
    result['errors'] = sum(1 for row in result['messages'] if row['severity'] == 'Error')
    if result['errors']: raise ValueError('Build errors; runtime skipped')
    result['compiler'] = str(project.project_settings.get_compilerversion())
    result['dependency_bindings'] = [{'name': r.name, 'namespace': r.namespace,
        'resolved': str(r.effective_resolution) if r.is_placeholder else r.name}
        for r in project.get_library_manager().references]
    if args.get('run', False):
        if not any('IPC_PLC.Sim.IPC_PLC.Application' in row['text'] for row in result['messages']):
            raise ValueError('Build did not identify the authorized simulator application')
        session = online.create_online_application(project.active_application)
        system.prompt_answers['QueryProgramChanged'] = PromptResult.Yes
        system.prompt_answers['QueryCreateApplication'] = PromptResult.Yes
        session.login(OnlineChangeOption.Never, True)
        result['bindings'] = dict((name, str(session.read_value(name))) for name in args.get('bind', []))
        session.start()
        result['observations'] = []
        started = DateTime.UtcNow
        for cycle in range(int(args.get('polls', 40))):
            system.delay(250)
            polling = [args[key] for key in ('done', 'report_state') if args.get(key)]
            values = dict((name, str(session.read_value(name))) for name in polling)
            result['observations'].append(values)
            done = not args.get('done') or values.get(args['done'], '').upper().split('#')[-1] == 'TRUE'
            if args.get('report_state'):
                done = done and any(state in values[args['report_state']] for state in ('WRITTEN', 'FAILED', 'DISABLED'))
            if done: break
            if (DateTime.UtcNow - started).TotalSeconds >= args.get('runtime_timeout_seconds', 75): break
        result['observations'].append({})
        for name in args['observe']:
            try: result['observations'][-1][name] = str(session.read_value(name))
            except Exception:
                result['failed_observation'] = name
                raise
        if args.get('capture_log'):
            count = int(str(session.read_value('GVL_QualificationLog.Count')).split('#')[-1])
            if count > 40: raise ValueError('Native log capture exceeds bounded read budget')
            result['log_hex'] = [str(session.read_value('GVL_QualificationLog.HexEntries[' + str(index) + ']')).strip("'") for index in range(1, count + 1)]
        result['runtime_seconds'] = (DateTime.UtcNow - started).TotalSeconds
        result['completed'] = done
        result['messages_after_run'] = [{'severity':str(message.severity), 'text':unicode(message.text)}
                                       for message in system.get_message_objects(category=category)]
    result['ok'] = True
except Exception:
    result['exception'] = traceback.format_exc()
finally:
    system.script_prompt_handling, system.log_prompt_details = prompt_preimage
    for key in prompt_keys:
        if key in prompt_answers: system.prompt_answers[key] = prompt_answers[key]
        elif key in system.prompt_answers: del system.prompt_answers[key]
    if session is not None:
        try:
            if session.application_state == ApplicationState.run: session.stop()
            session.logout()
        except Exception: result['cleanup_exception'] = traceback.format_exc()
    if parameter_preimage is not None:
        try:
            parameter_preimage[0].replace(new_text=parameter_preimage[1])
            result['parameter_restored'] = parameter_preimage[0].text == parameter_preimage[1]
        except Exception: result['parameter_restore_exception'] = traceback.format_exc()
    result['primary_unchanged'] = str(projects.primary.path) == original
    with io.open(args['report'], 'w', encoding='utf-8') as stream:
        stream.write(unicode(json.dumps(result, indent=2)))
mcp_result = json.dumps({'ok':result['ok'], 'errors':result.get('errors'), 'exception':result.get('exception'), 'report':args['report']})

