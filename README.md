# poetry-import
This CLI utility helps you migrate from Python pip requirements to Poetry pyproject.toml + poetry.lock.
It looks for and extracts information from setup.py and requirements files.  It is geared more towards pip-tools
generated requirements.

A pyproject.toml is generated from information discovered in setup.py and recognized dependency files.
Version constraints are preserved.

A skeleton poetry.lock is generated if a lockfile is detected in the project. This ensures your migrated project
ships with the exact same pinned/locked dependencies as before.

## Release Dependency Files
poetry-import will recognize the following files as top-level dependency files:
- requirements.in
- requirements.txt (if no requirements.in file exists)

## Dev Dependency Files
poetry-import will recognize the following files as top-level development dependency files:
- dev-requirements.in
- test-requirements.txt
- test_requirements.txt

## Lock files
- requirements.txt (if a requirements.in file exists)

## Installation
Use [pipx](https://github.com/pypa/pipx) to install.
`pipx install poetry-import`

## Usage
`poetry-import <path-to-project>`

If all goes well, follow-up instructions will be output like:
> Now run `poetry-lock --no-update` from .
or
> Now run `poetry-lock` from .

depending on if a lockfile was detected.

You then run the specified poetry command to flesh out the poetry.lock file.