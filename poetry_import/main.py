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
from typing import List
import re
import contextlib
import argparse
import toml
from packaging.markers import Marker
from distutils.core import run_setup
from distutils.dist import Distribution

# Consider:
#   Use a TOML reader/writer.
#   Append to existing TOML file and section
#   Overwrite/update existing entries.
# Milestone 5: Auto-detect all requirements files.
#
def main():
    parser = argparse.ArgumentParser(
        description='TODO BW DOCME.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('input_path')

    args = parser.parse_args()

    basepath = Path(args.input_path)
    depfile = determine_filepath(basepath, [
        'requirements.in',
        'requirements-to-freeze.txt'
    ])
    devdepfile = determine_filepath(basepath, [
        'dev-requirements.in',
        'test_requirements.in',
        'test-requirements.in',
        'test-requirements.txt',
        'test_requirements.txt'])
    setupfile = basepath / 'setup.py'
    lockfile = basepath / 'requirements.txt'

    if not depfile.exists() and lockfile.exists():
        print(f'"{depfile.name}" does not exist. Assuming "{lockfile.name}" is the top-level dependency file.')
        depfile = lockfile
        lockfile = None

    private_repo = get_private_repo()

    with open(basepath / 'pyproject.toml', 'w') as outfile:
        def _writeline(line = ''):
            outfile.write(line)
            outfile.write('\n')
        outfile.writeline = _writeline

        if setupfile.exists():
            import_setup(setupfile, outfile)
        else:
            write_boilerplate_tool_poetry_section(outfile)
        outfile.writeline()

        if private_repo:
            import_private_repo(outfile, private_repo)

        import_requirements(depfile, devdepfile, outfile)
        outfile.writeline()

        write_build_system(outfile)

    if lockfile and lockfile.exists():
        with open(basepath / 'poetry.lock', 'w') as outfile:
            import_lockfile(str(lockfile), private_repo, outfile)

    print('Operation complete!')
    if lockfile:
        print(f'Now run `poetry lock --no-update` from {basepath}')
    else:
        print(f'Now run `poetry lock` from {basepath}')


def determine_filepath(basepath: Path, filenames: List[str]) -> Path:
    for filename in filenames:
        filepath = basepath / filename
        if filepath.exists():
            return filepath
    return None


def import_setup(setupfile, outfile):
    print(f'Importing setup metadata from {setupfile}...')
    with working_directory(setupfile.parent.absolute()):
        distribution: Distribution = run_setup(setupfile.name, stop_after='config')
        meta = distribution.metadata
        version = str(meta.version)
        if not re.match(r"\d+\.\d+\.\d+", version):
            print(f'Invalid version format "{version}". Defaulting to "0.0.0"')
            version = '0.0.0'
        outfile.writeline('[tool.poetry]')
        outfile.writeline(f'name = "{meta.name}"')
        outfile.writeline(f'version = "{version}"')
        outfile.writeline(f'description = "{meta.description}"')
        outfile.writeline(f'repository = "{meta.url}"')
        email = meta.author_email or 'none@none.none'
        outfile.writeline(f'authors = ["{meta.author} <{email}>"]')


def write_boilerplate_tool_poetry_section(outfile):
    print(f'Generating boilerplate [tool.poetry] section. Be sure to fill in suitable values!')
    outfile.writeline('[tool.poetry]')
    outfile.writeline(f'name = "TODO-ADD-NAME"')
    outfile.writeline(f'version = "0.0.0"')
    outfile.writeline(f'description = "TODO-ADD-DESCRIPTION"')
    outfile.writeline(f'authors = ["none@none.none"]')


def import_private_repo(outfile, repository):
    repo_name, url = repository
    print(f'Using private repository "{repo_name}" at {url}')
    outfile.writeline('[[tool.poetry.source]]')
    outfile.writeline(f'name = "{repo_name}"')
    outfile.writeline(f'url = "{url}"')
    outfile.writeline('default = true')
    outfile.writeline()


def get_private_repo():
    poetry_config_file = Path.home() / '.config' / 'pypoetry' / 'config.toml'
    if not poetry_config_file.exists():
        return None

    poetry_config = toml.load(poetry_config_file)
    repositories = poetry_config.get('repositories')
    if not repositories:
        return None
    repositories_items = list(repositories.items())
    if not repositories_items:
        return None

    repository_item = repositories_items[0]
    return (repository_item[0], repository_item[1].get('url'))


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


def import_lockfile(lockfile, private_repo, outfile):
    pip_reqs = (req.requirement for req in parse_requirements(lockfile, None))
    reqs = list(pkg_resources.parse_requirements(pip_reqs))

    packages = []

    for req in reqs:
        package = {
            'name': req.project_name,
            'version': req.specs[0][1],
            'category': 'main',
            'optional': False,
            'python-versions': "*"
        }
        if private_repo:
            package['source'] = {
                'type': 'legacy',
                'url': private_repo[1],
                'reference': private_repo[0]
            }
        packages.append(package)

    lockfile_dict = {
        'package': packages,
        'metadata': {
            'lock-version': '1.1',
            'files': { package['name']: {} for package in packages }
        }
    }

    toml.dump(lockfile_dict, outfile)


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