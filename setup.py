import os
import runpy
import subprocess
from distutils.cmd import Command
from tempfile import TemporaryDirectory
from typing import List, Optional, Tuple, cast

from setuptools import find_packages, setup


class PyinstallerCommand(Command):
    description = "create a self-contained executable with PyInstaller"
    user_options = []  # type: List[Tuple[str, Optional[str], str]]

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass

    def run(self) -> None:
        with TemporaryDirectory() as temp_dir:
            subprocess.check_call(["python3", "-m", "venv", os.path.join(temp_dir, "env")])
            subprocess.check_call([os.path.join(temp_dir, "env/bin/pip"), "install", "."])
            subprocess.check_call([os.path.join(temp_dir, "env/bin/pip"), "install", "pyinstaller"])
            with open(os.path.join(temp_dir, "entrypoint.py"), "w") as f:
                f.write(
                    """
#!/usr/bin/env python3

from gitlab_multi_group_runner.cli import main


if __name__ == "__main__":
    main()
                    """.strip()
                )
            subprocess.check_call(
                [
                    os.path.join(temp_dir, "env/bin/pyinstaller"),
                    "--clean",
                    "--name=gitlab-multi-group-runner",
                    "--onefile",
                    "--strip",
                    os.path.join(temp_dir, "entrypoint.py"),
                ]
            )


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
    cmdclass={"bdist_pyinstaller": PyinstallerCommand},
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Utilities",
    ],
)
