import sys, os, glob, subprocess
# sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/src")

from pycparser import c_parser, c_ast


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
    if isinstance(ext, c_ast.Pragma):
      continue

  # ast.show()

  # break

# Top nodes: Typedef, Pragma, FuncDef, Decl
