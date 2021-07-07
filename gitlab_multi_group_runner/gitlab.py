import logging
import os
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, TextIO, Tuple, Union, cast

import yaml
from cerberus import Validator
from gitlab import MAINTAINER_ACCESS
from gitlab import Gitlab as _Gitlab
from gitlab.exceptions import GitlabGetError
from gitlab.v4.objects import Group as GitlabGroup
from gitlab.v4.objects import Project as GitlabProject
from gitlab.v4.objects import Runner as GitlabRunner
from gitlab.v4.objects import User as GitlabUser

from .config import ConfigValidationFailedError
from .utils import dump_config_as_yaml

logger = logging.getLogger(__name__)


MULTI_GROUP_RUNNER_CONFIG_FILENAME = "multi-group-runner-config.yml"

MULTI_GROUP_RUNNER_CONFIG_SCHEMA = {
    "runners": {
        "required": True,
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "ids": {"required": True, "type": "list", "schema": {"type": "integer"}},
                "groups_and_projects": {
                    "required": True,
                    "type": "list",
                    "schema": {
                        "type": "string",
                    },
                },
            },
        },
    },
}

MULTI_GROUP_RUNNER_EXAMPLE_CONFIG = {
    "runners": [
        {
            "ids": [5, 9],
            "groups_and_projects": ["mygroup", "myusername/myproject"],
        }
    ]
}


class NoConfigFileFoundError(Exception):
    pass


class NoMatchingProjectError(Exception):
    pass


class NoMatchingGroupError(Exception):
    pass


class NoMatchingRunnerError(Exception):
    pass


class NotASpecificRunnerError(Exception):
    pass


class NoMatchingUserError(Exception):
    pass


class Gitlab:
    def __init__(self, gitlab_url: str, private_token: str, dry_run: bool = False):
        self._gitlab = _Gitlab(gitlab_url, private_token=private_token)
        self._dry_run = dry_run
        self._projects_with_already_disabled_shared_runners: Set[int] = set()

    def get_project(self, project_id_or_path: Union[str, int]) -> GitlabProject:
        try:
            project = self._gitlab.projects.get(project_id_or_path)
        except GitlabGetError as e:
            if isinstance(project_id_or_path, int):
                raise NoMatchingProjectError(
                    'The project with id "{}" is not accessible.'.format(project_id_or_path)
                ) from e
            else:
                raise NoMatchingProjectError('The project "{}" is not accessible.'.format(project_id_or_path)) from e
        return project

    def get_group(self, group_id_or_path: Union[str, int]) -> GitlabGroup:
        try:
            group = self._gitlab.groups.get(group_id_or_path)
        except GitlabGetError as e:
            if isinstance(group_id_or_path, int):
                raise NoMatchingGroupError('The group with id "{}" is not accessible.'.format(group_id_or_path)) from e
            else:
                raise NoMatchingGroupError('The group "{}" is not accessible.'.format(group_id_or_path)) from e
        return group

    def get_group_projects(self, group_id_or_path: Union[str, int]) -> List[GitlabProject]:
        try:
            group = self._gitlab.groups.get(group_id_or_path)
        except GitlabGetError as e:
            if isinstance(group_id_or_path, int):
                raise NoMatchingGroupError('The group with id "{}" is not accessible.'.format(group_id_or_path)) from e
            else:
                raise NoMatchingGroupError('The group "{}" is not accessible.'.format(group_id_or_path)) from e
        group_projects = group.projects.list(all=True)
        projects = [self._gitlab.projects.get(group_project.id) for group_project in group_projects]
        return projects

    def get_runner(self, runner_id: int, check_if_project_type: bool = True) -> GitlabRunner:
        try:
            runner = self._gitlab.runners.get(runner_id)
        except GitlabGetError as e:
            raise NoMatchingRunnerError('The runner with id "{}" is not accessible.'.format(runner_id)) from e
        if check_if_project_type and runner.runner_type != "project_type":
            raise NotASpecificRunnerError(
                'The runner with id "{}" is not a specific / project type runner.'.format(runner_id)
            )
        return runner

    def get_user(self, user_id_or_name: Union[str, int]) -> GitlabUser:
        try:
            if isinstance(user_id_or_name, int):
                user_id = user_id_or_name
                user = self._gitlab.users.get(user_id)
            else:
                user_name = user_id_or_name
                user_list = self._gitlab.users.list(username=user_name)
                if user_list:
                    user = user_list[0]
                else:
                    raise NoMatchingUserError('The user "{}" is not accessible.'.format(user_id_or_name))
        except GitlabGetError as e:
            if isinstance(user_id_or_name, int):
                raise NoMatchingUserError('The user with id "{}" is not accessible.'.format(user_id_or_name)) from e
            else:
                raise NoMatchingUserError('The user "{}" is not accessible.'.format(user_id_or_name)) from e
        return user

    def get_project_members(self, project: GitlabProject, minimum_role: int = MAINTAINER_ACCESS) -> List[GitlabUser]:
        return [p for p in project.members_all.list(all=True) if p.access_level >= minimum_role]

    def is_any_user_in_project(
        self,
        users_or_groups: Iterable[Union[GitlabUser, GitlabGroup]],
        project: GitlabProject,
        minimum_role: int = MAINTAINER_ACCESS,
    ) -> bool:
        users = set()
        for user_or_group in users_or_groups:
            if isinstance(user_or_group, GitlabUser):
                users.add(user_or_group)
            else:
                users.update(
                    user for user in user_or_group.members_all.list(all=True) if user.access_level >= minimum_role
                )
        project_members = set(self.get_project_members(project, minimum_role))
        project_members_and_users = project_members & users
        if project_members_and_users:
            logger.debug(
                'The users %s are members of the project "%s"',
                tuple(user.username for user in project_members_and_users),
                project.path_with_namespace,
            )
            return True
        else:
            logger.debug(
                'None of the users %s is member of the project "%s"',
                [user.username for user in users],
                project.path_with_namespace,
            )
            return False

    def get_project_file(self, project: GitlabProject, file_path: str, branch: str) -> Optional[bytes]:
        directory_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        try:
            matching_files = [
                entry
                for entry in project.repository_tree(path=directory_path, ref=branch)
                if entry["name"] == file_name
            ]
            if matching_files:
                file_content = project.repository_raw_blob(matching_files[0]["id"])
                return cast(bytes, file_content)
        except GitlabGetError as e:
            logger.debug(str(e))
        return None

    def activate_runner_in_projects(
        self,
        runner_or_id: Union[int, GitlabRunner],
        projects: Iterable[GitlabProject],
        disable_shared_runners: bool = False,
    ) -> None:
        if isinstance(runner_or_id, int):
            runner = self.get_runner(runner_or_id)
        else:
            runner = runner_or_id
        for project in projects:
            if disable_shared_runners:
                if project.id not in self._projects_with_already_disabled_shared_runners:
                    if project.shared_runners_enabled:
                        if self._dry_run:
                            logger.info('Would disable shared runners in project "%s"', project.path_with_namespace)
                        else:
                            logger.info('Disable shared runners in project "%s"', project.path_with_namespace)
                            project.shared_runners_enabled = False
                            project.save()
                    else:
                        logger.info('Shared runners are already disabled in project "%s"', project.path_with_namespace)
                    self._projects_with_already_disabled_shared_runners.add(project.id)
            project_runners = project.runners.list(all=True)
            if runner.id not in (r.id for r in project_runners):
                if self._dry_run:
                    logger.info(
                        'Would enable runner "%s", (id: `%d`, tags: ["%s"]) in project "%s"',
                        runner.description,
                        runner.id,
                        '", "'.join(runner.tag_list),
                        project.path_with_namespace,
                    )
                else:
                    logger.info(
                        'Enable runner "%s", (id: `%d`, tags: ["%s"]) in project "%s"',
                        runner.description,
                        runner.id,
                        '", "'.join(runner.tag_list),
                        project.path_with_namespace,
                    )
                    project.runners.create({"runner_id": runner.id})
            else:
                logger.info(
                    'Runner "%s", (id: `%d`, tags: ["%s"]) is already enabled in project "%s"',
                    runner.description,
                    runner.id,
                    '", "'.join(runner.tag_list),
                    project.path_with_namespace,
                )


class MultiGroupRunnerConfig:
    def __init__(self, config_content: str):
        def parse_config(config_content: str) -> Dict[str, Any]:
            validator = Validator(MULTI_GROUP_RUNNER_CONFIG_SCHEMA)
            if not validator.validate(yaml.safe_load(config_content)):
                raise ConfigValidationFailedError(None, validator.errors)
            normalized_config_dict = validator.document
            return cast(Dict[str, Any], normalized_config_dict)

        self._config_dict = parse_config(config_content)

    def __iter__(self) -> Iterator[int]:
        return (runner_id for runner_config in self._config_dict["runners"] for runner_id in runner_config["ids"])

    def iter_runners_with_groups_and_projects(self) -> Iterator[Tuple[int, Iterable[str]]]:
        return (
            (runner_id, runner_config["groups_and_projects"])
            for runner_config in self._config_dict["runners"]
            for runner_id in runner_config["ids"]
        )


def assign_multi_group_runner(
    gitlab_url: str,
    private_token: str,
    allowed_runner_ids: Iterable[int],
    runner_config_repo_path: str,
    runner_config_repo_branch: str,
    allowed_projects_rules: Dict[str, Any],
    disable_shared_runners: bool,
    dry_run: bool = False,
) -> None:
    def preprocess_allowed_project_rules() -> Dict[str, Any]:
        processed_project_rules: Dict[str, Any] = {}
        if "one_member_of" in allowed_projects_rules:
            one_member_of: List[Union[GitlabGroup, GitlabUser]] = []
            for group_or_user_str in allowed_projects_rules["one_member_of"]:
                try:
                    user = gitlab.get_user(group_or_user_str)
                    logger.debug('Identifiied "%s" as GitLab user', group_or_user_str)
                    one_member_of.append(user)
                except NoMatchingUserError:
                    try:
                        group = gitlab.get_group(group_or_user_str)
                        logger.debug('Identifiied "%s" as GitLab group', group_or_user_str)
                        one_member_of.append(group)
                    except NoMatchingGroupError:
                        logger.warning('"%s" is neither a valid GitLab group nor user, skipping.', group_or_user_str)
            processed_project_rules["one_member_of"] = one_member_of
        return processed_project_rules

    def is_project_allowed(project: GitlabProject) -> bool:
        if "one_member_of" in allowed_projects_rules:
            if not gitlab.is_any_user_in_project(
                users_or_groups=allowed_projects_rules["one_member_of"], project=project, minimum_role=MAINTAINER_ACCESS
            ):
                return False
        return True

    gitlab = Gitlab(gitlab_url, private_token, dry_run)
    runner_config_project = gitlab.get_project(runner_config_repo_path)
    runner_config_content = gitlab.get_project_file(
        runner_config_project, MULTI_GROUP_RUNNER_CONFIG_FILENAME, runner_config_repo_branch
    )
    if runner_config_content is None:
        raise NoConfigFileFoundError(
            'Could not find a config file "{}" in the repository "{}", branch "{}".'.format(
                MULTI_GROUP_RUNNER_CONFIG_FILENAME, runner_config_repo_path, runner_config_repo_branch
            )
        )
    multi_group_runner_config = MultiGroupRunnerConfig(runner_config_content.decode("utf-8"))
    allowed_projects_rules = preprocess_allowed_project_rules()
    for runner_id, group_or_projects in multi_group_runner_config.iter_runners_with_groups_and_projects():
        if runner_id not in allowed_runner_ids:
            logger.warning(
                "The runner with id `%d` is not allowed to be assigned to other projects, skipping.", runner_id
            )
            continue
        try:
            runner = gitlab.get_runner(runner_id)
        except NoMatchingRunnerError:
            logger.warning("The runner with id `%d` is not accessible, skipping.", runner_id)
            continue
        except NotASpecificRunnerError:
            logger.warning("The runner with id `%d` is not a specific runner, skipping.", runner_id)
            continue
        for group_or_project in group_or_projects:
            try:
                projects = gitlab.get_group_projects(group_or_project)
            except NoMatchingGroupError:
                try:
                    projects = [gitlab.get_project(group_or_project)]
                except NoMatchingProjectError:
                    logger.warning('"%s" is neither an accessible group nor project, skipping.', group_or_project)
                    continue
            allowed_projects: List[GitlabProject] = []
            for project in projects:
                if not is_project_allowed(project):
                    logger.warning(
                        'It is not allowed to assign the runner with id `%d` to the project "%s", skipping.',
                        runner_id,
                        project.path_with_namespace,
                    )
                    continue
                allowed_projects.append(project)
            gitlab.activate_runner_in_projects(runner, allowed_projects, disable_shared_runners)


def write_example_multi_group_runner_config(config_filepath_or_file: Union[str, TextIO]) -> None:
    if isinstance(config_filepath_or_file, str):
        with open(config_filepath_or_file, "w", encoding="utf-8") as config_file:
            dump_config_as_yaml(MULTI_GROUP_RUNNER_EXAMPLE_CONFIG, config_file)
    else:
        config_file = config_filepath_or_file
        dump_config_as_yaml(MULTI_GROUP_RUNNER_EXAMPLE_CONFIG, config_file)
