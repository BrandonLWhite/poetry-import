# TODO BW: The order here is important, otherwise an exception is thrown
# _distutils_hack/__init__.py:17: UserWarning: Distutils was imported before Setuptools, but importing Setuptools also
# replaces the `distutils` module in `sys.modules`. This may lead to undesirable behaviors or errors. To avoid these
# issues, avoid using distutils directly, ensure that setuptools is installed in the traditional way
# (e.g. not an editable install), and/or make sure that setuptools is always imported before distutils.
# import setuptools
import os
os.environ['SETUPTOOLS_USE_DISTUTILS']='stdlib'

from pip._internal.req import parse_requirements
import pkg_resources

from pathlib import Path
import contextlib
import os
import argparse
from packaging.markers import Marker
from distutils.core import run_setup
from distutils.dist import Distribution

# Consider:
#   Use a TOML reader/writer.
#   Append to existing TOML file and section
#   Overwrite/update existing entries.
# Milestone 4: Import requirements.txt to generate poetry.lock
# Milestone 5: Auto-detect all requirements files.
#
def main():
    parser = argparse.ArgumentParser(
        description='TODO BW DOCME.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('input_path')
    # parser.add_argument('depfile')
    # parser.add_argument('devfile')

    args = parser.parse_args()

    filepath = Path(args.input_path)
    depfile = filepath / 'requirements.in'
    devdepfile = filepath / 'dev-requirements.in'
    setupfile = filepath / 'setup.py'
    lockfile = filepath / 'requirements.txt'

    with open(filepath / 'pyproject.toml', 'w') as outfile:
        def _writeline(line = ''):
            outfile.write(line)
            outfile.write('\n')
        outfile.writeline = _writeline

        if setupfile.exists():
            import_setup(setupfile, outfile)
            outfile.writeline()

        import_requirements(depfile, devdepfile, outfile)
        outfile.writeline()
        write_build_system(outfile)


def import_setup(setupfile, outfile):
    print(f'Importing setup metadata from {setupfile}...')
    with working_directory(setupfile.parent.absolute()):
        distribution: Distribution = run_setup(setupfile.name, stop_after='config')
        meta = distribution.metadata
        outfile.writeline('[tool.poetry]')
        outfile.writeline(f'name = "{meta.name}"')
        outfile.writeline(f'version = "{meta.version}"')
        outfile.writeline(f'description = "{meta.description}"')
        outfile.writeline(f'repository = "{meta.url}"')
        email = meta.author_email or 'none@none.none'
        outfile.writeline(f'authors = ["{meta.author} <{email}>"]')


def import_requirements(depfile, devdepfile, outfile):
    print(f'Importing release requirements from {depfile}...')
    outfile.writeline('[tool.poetry.dependencies]')
    outfile.writeline('python = "3.7.*"')
    translate_requirements(str(depfile), outfile)

    print(f'Importing dev/test requirements from {devdepfile}...')
    outfile.writeline()
    outfile.writeline('[tool.poetry.dev-dependencies]')
    translate_requirements(str(devdepfile), outfile)


def translate_requirements(depfilename: str, outfile):
    with open(depfilename) as depfile:
        pip_reqs = parse_requirements(depfilename, None)

        # Use pip to parse the requirements file, and ignore anything that comes from a `-c requirements.txt` constraint
        # specification
        requirements = [req.requirement for req in pip_reqs if not req.constraint]
        reqs = list(pkg_resources.parse_requirements(requirements))
        for req in reqs:
            name = req.project_name
            if '.' in name:
                name = f'"{name}"'
            toml_spec = get_toml_spec(req)
            toml_line = f'{name} = {toml_spec}'
            outfile.writeline(toml_line)


def get_toml_spec(requirement: pkg_resources.Requirement) -> str:
    spec = requirement.specifier or '*'
    if requirement.marker:
        marker: Marker = requirement.marker
        marker_parts = marker._markers[0]
        marker_var = str(marker_parts[0])
        marker_spec = ''.join(str(part) for part in marker_parts[1:])
        # Implement support for other marker vars, possibly using a lookup map.
        if marker_var == 'python_version':
            return f'{{ version = "{spec}", python = "{marker_spec}" }}'
        else:
            print(f'Ignoring unsupportor environment marker "{marker_var}"')
    return f'"{spec}"'


def write_build_system(outfile):
    outfile.writeline('[build-system]')
    outfile.writeline('requires = ["poetry-core>=1.0.0"]')
    outfile.writeline('build-backend = "poetry.core.masonry.api"')


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


if __name__ == '__main__':
    main()