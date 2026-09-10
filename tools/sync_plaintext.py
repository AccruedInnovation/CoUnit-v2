"""Shared ScriptEngine plaintext tree synchronization; no implicit export path."""
import io, os, re
def read(path):
    with io.open(path, 'r', encoding='utf-8-sig') as stream:
        return stream.read()

def code(text):
    return re.sub(r'\(\*.*?\*\)|//[^\r\n]*|\{[^}]*\}', '', text, flags=re.S).strip()

def sync(parent, directory):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isdir(path):
            continue
        result['current_path'] = path
        decl = os.path.join(path, name + '.DEC.exp')
        imp = os.path.join(path, name + '.IMP.exp')
        matches = [x for x in parent.get_children(False) if x.get_name() == name]
        if len(matches) > 1:
            raise ValueError('Ambiguous native object ' + path)
        obj = matches[0] if matches else None
        declaration = read(decl) if os.path.isfile(decl) else None
        if obj is None:
            if declaration is None:
                parent.create_folder(name)
                obj = next(x for x in parent.get_children(False) if x.get_name() == name)
            else:
                kind = code(declaration).split()[0].upper()
                if kind == 'FUNCTION_BLOCK': obj = parent.create_function_block(name)
                elif kind == 'FUNCTION': obj = parent.create_function(name, 'BOOL')
                elif kind == 'PROGRAM': obj = parent.create_program(name)
                elif kind == 'TYPE': obj = parent.create_dut(name)
                elif kind == 'VAR_GLOBAL': obj = parent.create_gvl(name)
                elif kind == 'INTERFACE': obj = parent.create_interface(name)
                elif kind == 'METHOD': obj = parent.create_method(name)
                elif kind == 'PROPERTY': obj = parent.create_property(name)
                else: raise ValueError('Cannot create declaration kind ' + kind + ': ' + path)
            result['created'].append(path)
        for filename, attr in [(decl, 'textual_declaration'), (imp, 'textual_implementation')]:
            if os.path.isfile(filename):
                # Native library compilation uses CRLF line offsets, including after save.
                expected = read(filename).replace('\r\n', '\n').replace('\n', '\r\n')
                document = getattr(obj, attr)
                if document.text != expected:
                    document.replace(new_text=expected)
                if document.text.replace('\r\n', '\n') != expected.replace('\r\n', '\n'):
                    raise ValueError('Native read-back differs: ' + filename)
                result['sections'] += 1
        sync(obj, path)

