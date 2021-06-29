import os
import runpy
from typing import Optional, cast

from setuptools import find_packages, setup


def get_version_from_pyfile(version_file: str = "gitlab_multi_group_runner/_version.py") -> str:
    file_globals = runpy.run_path(version_file)
    return cast(str, file_globals["__version__"])


def get_long_description_from_readme(readme_filename: str = "README.md") -> Optional[str]:
    long_description = None
    if os.path.isfile(readme_filename):
        with open(readme_filename, "r", encoding="utf-8") as readme_file:
            long_description = readme_file.read()
    return long_description


version = get_version_from_pyfile()
long_description = get_long_description_from_readme()

setup(
    name="gitlab-multi-group-runner",
    version=version,
    packages=find_packages(),
    python_requires="~=3.6",
    install_requires=["cerberus", "python-gitlab", "pyyaml", "yacl[colored_exceptions]"],
    entry_points={
        "console_scripts": [
            "gitlab-multi-group-runner = gitlab_multi_group_runner.cli:main",
        ]
    },
    author="Ingo Meyer",
    author_email="i.meyer@fz-juelich.de",
    description="A helper to assign a GitLab runner to multiple groups and projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/sciapp/gitlab-multi-group-runner",
    keywords=["gitlab", "ci", "runner", "multi-group"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Utilities",
    ],
)
