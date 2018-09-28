
# sm64.json

sm64.json is a file containing descriptions for data structures in Super
Mario 64.
It includes:
- struct definitions (WIP)
- global variables and their types (WIP)
- functions and their types (WIP)
- object fields (WIP)

It is generated from the SM64 matching decomp, and as such will become more
complete and correct over time.

Notably, it does not contain any global addresses. Instead, these addresses
should be looked up in a generated .map file from the decomp.

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
