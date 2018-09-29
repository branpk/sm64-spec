import sys, os, glob, subprocess, json
# sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/src")

from pycparser import c_parser, c_ast


# TODO:
#   Type/global merging (e.g. function decls w/o named params)
#   Object fields
#   Enum parsing
#   Define parsing


def parse_c_int(s):
  s = s.strip()
  if s[0] == '-':
    return -parse_c_int(s[1:])
  elif s.startswith('0x'):
    return int(s, base=16)
  elif s.startswith('0'):
    return int(s, base=8)
  else:
    return int(s, base=10)
  raise NotImplementedError('parse_c_int: ' + str(s))

def eval_c_int(s):
  if type(s) is c_ast.Constant:
    assert s.type == 'int'
    return parse_c_int(s.value)
  elif type(s) is c_ast.BinaryOp:
    if s.op == '+':
      return eval_c_int(s.left) + eval_c_int(s.right)
    elif s.op == '-':
      return eval_c_int(s.left) - eval_c_int(s.right)
  raise NotImplementedError('eval_c_int: ' + str(s))


data = {
  'struct': {},
  'union': {},
  'typedef': {},
  'global': {},
}

primitive_types = {
  'char': 1,
  's8': 1,
  'u8': 1,
  's16': 2,
  'u16': 2,
  's32': 4,
  'u32': 4,
  's64': 8,
  'u64': 8,
  'f32': 4,
  'f64': 8,
  'void': 4,
  'size_t': 4,
}

c_primitives = {
  'signed char': 's8',
  'unsigned char': 'u8',
  'short': 's16',
  'unsigned short': 'u16',
  'int': 's32',
  'unsigned int': 'u32',
  'long int': 's32',
  'long long int': 's64',
  'float': 'f32',
  'double': 'f64',
}

def get_struct_size(fields):
  return max(map(lambda f: get_type_size_and_align(f['type'])[0] + f['offset'], fields.values()))

def get_union_size(fields):
  return max(map(lambda f: get_type_size_and_align(f['type'])[0], fields.values()))

def get_struct_align(fields):
  return max(map(lambda f: get_type_size_and_align(f['type'])[1], fields.values()))

def get_real_type(type_):
  if type_['kind'] == 'sym':
    return get_real_type(data[type_['symtype']][type_['name']])
  return type_

def get_type_size_and_align(type_):
  type_ = get_real_type(type_)

  if type_['kind'] == 'prim':
    size = primitive_types[type_['name']]
    return size, size
  elif type_['kind'] == 'struct':
    return get_struct_size(type_['def']), get_struct_align(type_['def'])
  elif type_['kind'] == 'union':
    return get_union_size(type_['def']), get_struct_align(type_['def'])
  elif type_['kind'] == 'ptr':
    return 4, 4
  elif type_['kind'] == 'array':
    size, align = get_type_size_and_align(type_['base'])
    return type_['len'] * size, align
  elif type_['kind'] == 'func':
    pass

  raise NotImplementedError('get_type_size_and_align: ' + str(type_))

def get_struct_def(decls, union=False):
  defn = {}
  offset = 0

  for decl in decls:
    assert type(decl) is c_ast.Decl

    name = decl.name
    type_ = get_type_from_decl(decl.type)
    if name is not None:
      size, align = get_type_size_and_align(type_)
      if offset % align != 0:
        offset += align - (offset % align)
      
      defn[name] = {'type': type_, 'offset': offset}

      if not union:
        offset += size

  return defn

def get_param_type(decl):
  type_ = get_type_from_decl(decl)
  real_type = get_real_type(type_)
  if real_type['kind'] == 'array':
    return {'kind': 'ptr', 'base': type_}
  if real_type['kind'] == 'prim' and real_type['name'] == 'void':
    return None
  return type_

def get_param_list(param_list):
  if param_list is None:
    return [], True
  assert type(param_list) is c_ast.ParamList

  params = []
  variadic = False
  for param in param_list.params:

    if type(param) in [c_ast.Decl, c_ast.Typename]:
      param_name = '' if param.name is None else param.name
      param_type = get_param_type(param.type)
      if param_type is not None:
        params.append([param_name, param_type])
      continue

    elif type(param) is c_ast.EllipsisParam:
      variadic = True
      continue
    
    raise NotImplementedError('get_param_list: ' + str(param))

  return params, variadic

def get_type(type_):
  if type(type_) is c_ast.IdentifierType:
    name = ' '.join(type_.names)
    if name in c_primitives:
      name = c_primitives[name]
    if name in primitive_types:
      return {'kind': 'prim', 'name': name}
    return {'kind': 'sym', 'symtype': 'typedef', 'name': name}

  elif type(type_) in [c_ast.Struct, c_ast.Union]:
    name = type_.name
    symtype = 'struct' if type(type_) is c_ast.Struct else 'union'
    if type_.decls is None:
      return {'kind': 'sym', 'symtype': symtype, 'name': name} 
    result = {
      'kind': symtype,
      'def': get_struct_def(type_.decls, union=type(type_) is c_ast.Union)
    }
    if name is not None:
      data[symtype][name] = result
      result = {'kind': 'sym', 'symtype': symtype, 'name': name}
    return result

  elif type(type_) is c_ast.Enum:
    return {'kind': 'prim', 'name': 's32'}

  raise NotImplementedError('get_type: ' + str(type_))

def get_type_from_decl(decl):
  if type(decl) is c_ast.TypeDecl:
    return get_type(decl.type)

  elif type(decl) is c_ast.ArrayDecl:
    if decl.dim is None:
      length = -1
    else:
      length = eval_c_int(decl.dim)
    return {'kind': 'array', 'len': length, 'base': get_type_from_decl(decl.type)}

  elif type(decl) in [c_ast.Struct, c_ast.Union]:
    return get_type(decl)

  elif type(decl) is c_ast.PtrDecl:
    return {'kind': 'ptr', 'base': get_type_from_decl(decl.type)}

  elif type(decl) is c_ast.FuncDecl:
    params, variadic = get_param_list(decl.args)
    return {'kind': 'func', 'ret': get_type_from_decl(decl.type), 'params': params, 'variadic': variadic}

  elif type(decl) is c_ast.Enum:
    return {'kind': 'prim', 'name': 's32'}

  raise NotImplementedError('get_type_from_decl: ' + str(decl))

def process_ext(ext):
  if type(ext) is c_ast.Pragma:
    return

  elif type(ext) is c_ast.Typedef:
    name = ext.name
    if name in primitive_types:
      return
    type_ = get_type_from_decl(ext.type)
    assert name is not None
    data['typedef'][name] = type_
    return

  elif type(ext) is c_ast.Decl:
    name = ext.name
    type_ = get_type_from_decl(ext.type)
    if name is not None:
      data['global'][name] = {'type': type_}
    return

  elif type(ext) is c_ast.FuncDef:
    process_ext(ext.decl)
    return

  raise NotImplementedError('process_ext: ' + str(ext))


cppflags = [
  '-DVERSION_JP=1',
  '-Wno-unknown-warning-option',
  '-I' + os.path.normpath('extern/sm64_source/include'),
  '-I.', # For placeholder text_strings.h
]

srcpaths = [
  'src',
  'src/libultra',
  'src/goddard',
  'include',
]

cfiles = []
for path in srcpaths:
  cfiles += glob.glob(os.path.normpath('extern/sm64_source/' + path + '/*.c'))

if len(cfiles) == 0:
  print('Error: No input files (did you checkout sm64_source?)')
  quit(1)


parser = c_parser.CParser()

for i in range(len(cfiles)):
  cfile = cfiles[i]
  filename = cfile[len('extern/sm64_source/'):]
  print('(%d/%d) %s' % (i+1, len(cfiles), filename))

  ofile = 'build/' + filename
  if not os.path.isdir(os.path.dirname(ofile)):
    os.makedirs(os.path.dirname(ofile))

  cmd = 'gcc -E ' + cfile + ' ' + ' '.join(cppflags) + ' -o ' + ofile
  subprocess.run(cmd, shell=True, check=True)

  with open(ofile, 'r') as f:
    ctext = f.read()
  ctext = ctext.replace('__attribute__((unused))', '')

  ast = parser.parse(ctext, filename=filename)

  for ext in ast.ext:
    process_ext(ext)

with open('sm64.json', 'w') as f:
  f.write(json.dumps(data, separators=(',',':')))
with open('sm64_pretty.json', 'w') as f:
  f.write(json.dumps(data, indent=2))
