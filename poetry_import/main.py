from pathlib import Path
import contextlib
import os
import argparse
import pkg_resources
from packaging.markers import Marker
from distutils.core import run_setup
from distutils.dist import Distribution

# Consider:
#   Use a TOML reader/writer.
#   Append to existing TOML file and section
#   Overwrite/update existing entries.
# Milestone 3: Import setup.py to generate initial pyproject.toml
# Milestone 4: Auto-detect all requirements files.
#
def main():
    parser = argparse.ArgumentParser(
        description='TODO BW DOCME.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('depfile')
    parser.add_argument('devfile')
    args = parser.parse_args()

    with open('pyproject.out.toml', 'w') as outfile:
        translate_requirements(args.depfile, '[tool.poetry.dependencies]', outfile)
        outfile.write('\n')
        translate_requirements(args.devfile, '[tool.poetry.dev-dependencies]', outfile)

    # TODO: If setup.py file exists.
    with working_directory('./tests/data/'):
        distribution: Distribution = run_setup('setup.py')
        print(distribution.metadata.name)
        print(distribution.metadata.description)
        print(distribution.metadata.version)
        print(distribution.metadata.author_email)
        print(distribution.metadata.url)

    # packages=find_packages(exclude=['tests*']),


def translate_requirements(depfilename: str, section_name: str, outfile):
    with open(depfilename) as depfile:
        outfile.write(section_name)
        outfile.write('\n')
        reqs = list(pkg_resources.parse_requirements(depfile.readlines()))
        for req in reqs:
            # TODO BW : add quotes if there are dots in the name.
            toml_spec = get_toml_spec(req)
            toml_line = f'{req.project_name} = {toml_spec}'
            outfile.write(toml_line)
            outfile.write('\n')


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


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)