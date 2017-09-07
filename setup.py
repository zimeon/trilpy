"""Setup for trilpy."""
from setuptools import setup, Command
import os
import re

# Extract version number
verfile = open("trilpy/_version.py", "rt").read()
match = re.search(r"^__version__ = '(\d\.\d.\d+(\.\d+)?)'",
                  verfile, re.MULTILINE)
if match:
    version = match.group(1)
else:
    raise RuntimeError("Unable to find version string")


class Coverage(Command):
    """Class to allow coverage run from setup."""

    description = "run coverage"
    user_options = []

    def initialize_options(self):
        """Empty initialize_options."""
        pass

    def finalize_options(self):
        """Empty finalize_options."""
        pass

    def run(self):
        """Run coverage program."""
        os.system("coverage run --source=trilpy setup.py test")
        os.system("coverage report")
        os.system("coverage html")
        print("See htmlcov/index.html for details.")

setup(
    name='trilpy',
    version=version,
    author='Simeon Warner',
    author_email='simeon.warner@cornell.edu',
    packages=['trilpy'],
    package_data={'trilpy': ['static/*']},
    scripts=['trilpy.py'],
    classifiers=["Development Status :: 2 - Pre-Alpha",
                 "Intended Audience :: Developers",
                 "Operating System :: OS Independent",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6",
                 "Topic :: Internet :: WWW/HTTP",
                 "Topic :: Software Development :: "
                 "Libraries :: Python Modules",
                 "Environment :: Web Environment"],
    url='https://github.com/zimeon/trilpy',
    description='trilpy - A Fedora/LDP test implementation',
    long_description=open('README.md').read(),
    install_requires=[
        "negotiator2",
        "rdflib",
        "tornado",
        "uuid",
        "requests"
    ],
    test_suite="tests",
    cmdclass={
        'coverage': Coverage,
    },
)
