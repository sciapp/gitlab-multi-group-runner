import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from yacl import TerminalColorCodes, setup_colored_exceptions, setup_colored_stderr_logging

from ._version import __version__
from .config import DEFAULT_CONFIG_FILEPATH, Config, ConfigValidationFailedError, config
from .gitlab import (
    NoConfigFileFoundError,
    NoMatchingGroupError,
    NoMatchingProjectError,
    NoMatchingRunnerError,
    assign_multi_group_runner,
    write_example_multi_group_runner_config,
)

logger = logging.getLogger(__name__)


class NoMatchingRunnerConfigError(Exception):
    pass


def get_argumentparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
%(prog)s assigns specific GitLab runners to a given set of projects and groups.
""",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        dest="all_config_repositories",
        help="run with all config repositories in the given config file",
    )
    parser.add_argument("--debug", action="store_true", dest="debug", help="print debug messages")
    parser.add_argument(
        "-f",
        "--config-file",
        action="store",
        dest="config_filepath",
        default=DEFAULT_CONFIG_FILEPATH,
        help='custom configuration file path (default: "%(default)s")',
    )
    parser.add_argument("-n", "--dry-run", action="store_true", dest="dry_run", help="only show what would be executed")
    parser.add_argument(
        "--print-example-config",
        action="store_true",
        dest="print_example_config",
        help="print an example configuration to stdout and exit",
    )
    parser.add_argument(
        "--print-example-repo-config",
        action="store_true",
        dest="print_example_repo_config",
        help="print an example configuration for a multi group runner config repository to stdout and exit",
    )
    parser.add_argument(
        "-V", "--version", action="store_true", dest="print_version", help="print the version number and exit"
    )
    parser.add_argument(
        "config_repository_path",
        action="store",
        nargs="?",
        help='path of the multi group runner config repository in GitLab, for example "myusername/myconfigrepo"',
    )
    return parser


def parse_arguments() -> argparse.Namespace:
    parser = get_argumentparser()
    args = parser.parse_args()
    return args


def check_arguments(args: argparse.Namespace) -> None:
    if args.print_example_config and args.print_example_repo_config:
        logger.error('"--print-example-config" and "--print-example-repo-config" cannot be passed together.')
        sys.exit(1)


def setup_logging(debug: bool = False) -> None:
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        setup_colored_stderr_logging(keyword_colors={r"`([^`]+)`": TerminalColorCodes.cyan})
    else:
        logging.basicConfig(level=logging.INFO)
        setup_colored_stderr_logging(
            format_string="[%(levelname)s] %(message)s", keyword_colors={r"`([^`]+)`": TerminalColorCodes.cyan}
        )
    setup_colored_exceptions()


def load_config(args: argparse.Namespace) -> None:
    config(args.config_filepath)


def find_matching_runner_config(all_runner_configs: List[Dict[str, Any]], repo_path: str) -> Optional[Dict[str, Any]]:
    for runner_config in all_runner_configs:
        if runner_config["config_repo"]["path"] == repo_path:
            return runner_config
    return None


def main() -> None:
    args = parse_arguments()
    setup_logging(args.debug)
    check_arguments(args)
    if args.print_version:
        print("{}, version {}".format(os.path.basename(sys.argv[0]), __version__))
        sys.exit(0)
    elif args.print_example_config:
        Config.write_example_config(sys.stdout)
        sys.exit(0)
    elif args.print_example_repo_config:
        write_example_multi_group_runner_config(sys.stdout)
        sys.exit(0)
    try:
        load_config(args)
    except ConfigValidationFailedError as e:
        logger.error(str(e))
        sys.exit(3)
    if args.config_repository_path is None and not args.all_config_repositories:
        logger.error(
            "Please pass a config repository as first positional parameter or use the `--all` option. "
            "Run with `--help` for more details."
        )
        sys.exit(1)
    exceptions = (
        NoMatchingRunnerConfigError,
        NoConfigFileFoundError,
        NoMatchingProjectError,
        NoMatchingGroupError,
        NoMatchingRunnerError,
    )
    try:
        config_general = config()["general"]
        config_gitlab = config()["gitlab"]
        if args.all_config_repositories:
            runner_configs = config()["runners"]
        else:
            matching_runner_config = find_matching_runner_config(config()["runners"], args.config_repository_path)
            if matching_runner_config is None:
                raise NoMatchingRunnerConfigError(
                    'Could not find a matching configuration entry for the configuration repository "{}".'.format(
                        args.config_repository_path
                    )
                )
            runner_configs = [matching_runner_config]
        for runner_config in runner_configs:
            assign_multi_group_runner(
                config_gitlab["url"],
                config_gitlab["auth_token"],
                runner_config["ids"],
                runner_config["config_repo"]["path"],
                runner_config["config_repo"]["branch"],
                runner_config["allowed_projects_rules"],
                config_general["disable_shared_runners"],
                args.dry_run,
            )
    except exceptions as e:
        logger.error(str(e))
        for i, exception_class in enumerate(exceptions, start=4):
            if isinstance(e, exception_class):
                sys.exit(i)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
