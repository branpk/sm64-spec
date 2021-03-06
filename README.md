
# sm64.json

sm64.json is a file containing descriptions for data structures in Super
Mario 64.
It includes:
- struct definitions
- global variables and their types
- functions and their types
- object fields (WIP)

It is generated from the SM64 matching decomp, and as such will become more
complete and correct over time.

Notably, it does not contain any global addresses. Instead, these addresses
should be looked up in a generated .map file from the decomp.

sm64.json contains a minified version of the data, and sm64_pretty.json contains
an indented version.

## Generating sm64.json

If you want to update sm64.json with new data from the decomp, first make sure
you have the following dependencies:

* gcc (for the preprocessor)
* Python 3
* pycparser (`pip install pycparser`)
* sm64_source (use `--recursive` when cloning)

As of the time of writing this, sm64_source is a private repository. If you
don't have access to this repository, you will not be able to build sm64.json.

Then run:
```
python3 update.py
```

## Format

sm64.json parses to a map with five entries: `struct`, `union`, `typedef`, `global`,
and `object_field`. Each of these is defined in later sections.

### Types

A type is represented by a map. The `kind` field dictates what sort of type it
is. The possibilities are:

* `{"kind": "prim",   "name": <primitive name>}`
* `{"kind": "struct", "def": <struct definition>, "size": <struct size>}`
* `{"kind": "union",  "def": <struct definition>, "size": <struct size>}`
* `{"kind": "ptr",    "base": <base type>}`
* `{"kind": "array",  "len": <array length or -1>, "base": <base type>}`
* `{"kind": "func",   "ret": <return type>, "params": <param list>, "variadic": <bool>}`
* `{"kind": "sym",    "symtype": <symbol type>, "name": <symbol name>}`

The primitive names are:
`s8`,
`u8`,
`s16`,
`u16`,
`s32`,
`u32`,
`s64`,
`u64`,
`f32`,
`f64`,
`void`

A struct definition is a map from field names to a map of the form
`{"type": <type>, "offset": <offset>}`. For example:
```
{
  "x": {"type": {"kind": "prim", "name": "f32"}, "offset": 0},
  "y": {"type": {"kind": "prim", "name": "f32"}, "offset": 4},
  "z": {"type": {"kind": "prim", "name": "f32"}, "offset": 8}
}
```
The offsets can be overlapping in the case of unions.

A param list is a list with elements of the form `[<param name>, <param type>]`.
If a parameter is unnamed, the name will be `""`.
If the function is variadic or declared with an empty parameter list in C, then
the "variadic" field is true.
Unlike C, we differentiate between arrays and pointers in parameters; parameters
with array type in C are translated into pointers.

A symbol is a reference to a named struct, union, or typedef. The symbol types are
"struct", "union", and "typedef". These symbols are looked up in the corresponding
file section.

### struct, union, and typedef

These three sections each contain a map from symbol name to a type. For structs
and unions, these types must have kind `struct` or `union` respectively.

For example, the following code:
```
typedef struct A {
  s32 x;
  s32 y;
} B;
union C {
  s32 z;
  s32 w;
};
```
would result in the following sections:
```
{
  "struct": {
    "A": {
      "kind": "struct",
      "def": {
        "x": {"type": {"kind": "prim", "name": "s32"}, "offset": 0},
        "y": {"type": {"kind": "prim", "name": "s32"}, "offset": 4}
      }
    }
  },
  "union": {
    "C": {
      "kind": "union",
      "def": {
        "z": {"type": {"kind": "prim", "name": "s32"}, "offset": 0},
        "w": {"type": {"kind": "prim", "name": "s32"}, "offset": 0}
      }
    }
  },
  "typedef": {
    "B": {"kind": "sym", "symtype": "struct", "name": "A"}
  }
}
```

### global

The `global` section is a map from variable and function names to a map
containing a "type" entry. For example:
```
"gGlobalTimer": {"type": {"kind": "prim", "name": "u32"}},

"mario_drop_held_object": {
  "type": {
    "kind": "func",
    "ret": {"kind": "prim", "name": "void"},
    "params": [
      ["m", {"kind": "ptr", "base": {"kind": "sym", "symtype": "struct", "name": "MarioState"}}]
    ]
  }
}
```

### object_field (not implemented)

The `object_field` section describes object fields for each kind of object.

Each entry has a key corresponding to the object name - for example "bAbcDef" would
have an entry "AbcDef". There is an additional entry "common" that contains
data that is not associated with a single object.

The object field names are taken from the C macros, with the "oObjectName" stripped
away.

Each object field maps to a map containing a "type" and "index" keys. The index
is a list `[n, k]`.
`n` is the 32-bit field index (`0`-`0x4F`), and `k` describes the index of the
field within that member.
Specifically, the address of the field is computed as:
```
<raw data base ptr> + 4*n + k*<size of field type>
```

For example:
```
"common": {
  "PosX": {"type": {"kind": "prim", "name": "f32"}, "index": [6, 0]}
},

"Mario": {
  "Unk1AE": {"type": {"kind": "prim", "name": "s16"}, "index": [30, 1]}
}
```
(These are made-up examples.)
