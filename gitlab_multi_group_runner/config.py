import os
from copy import deepcopy
from pprint import pformat
from typing import Any, Dict, Optional, TextIO, Union, cast

import yaml
from cerberus import Validator
from cerberus.errors import ErrorList as CerberusErrorList

from .utils import dump_config_as_yaml, recursive_update

DEFAULT_CONFIG_FILEPATH = "/etc/gitlab_multi_group_runnerrc.yml"

CONFIG_SCHEMA = {
    "general": {
        "required": False,
        "type": "dict",
        "schema": {
            "disable_shared_runners": {"required": False, "type": "boolean"},
        },
    },
    "gitlab": {
        "required": True,
        "type": "dict",
        "schema": {
            "url": {"required": True, "type": "string"},
            "auth_token": {"required": True, "type": "string"},
        },
    },
    "runners": {
        "required": True,
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "ids": {"required": True, "type": "list", "schema": {"type": "integer"}},
                "config_repo": {
                    "required": True,
                    "type": "dict",
                    "schema": {
                        "path": {"required": True, "type": "string"},
                        "branch": {"required": True, "type": "string"},
                    },
                },
                "allowed_projects_rules": {
                    "required": True,
                    "type": "dict",
                    "schema": {
                        "one_member_of": {"required": False, "type": "list", "schema": {"type": "string"}},
                    },
                },
            },
        },
    },
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "disable_shared_runners": True,
    },
}

EXAMPLE_CONFIG = {
    "general": {
        "disable_shared_runners": True,
    },
    "gitlab": {
        "url": "https://mygitlab.com",
        "auth_token": "xxxxxxxxxxxxxxxxxxxx",
    },
    "runners": [
        {
            "ids": [1, 3],
            "config_repo": {
                "path": "administration/my-multi-group-runners",
                "branch": "master",
            },
            "allowed_projects_rules": {
                "one_member_of": ["my-group-name", "my-user-name"],
            },
        }
    ],
}


class ConfigValidationFailedError(Exception):
    def __init__(self, config_filepath: Optional[str], errors: CerberusErrorList):
        self._config_filepath = config_filepath
        self._errors = errors
        if self._config_filepath is not None:
            message = 'Could not validate the config file "{}", error:\n{}'.format(config_filepath, pformat(errors))
        else:
            message = "Could not validate the configuration, error:\n{}".format(pformat(errors))
        super().__init__(message)

    @property
    def config_filepath(self) -> Optional[str]:
        return self._config_filepath

    @property
    def errors(self) -> CerberusErrorList:
        return self._errors


class Config:
    @classmethod
    def write_example_config(cls, config_filepath_or_file: Union[str, TextIO]) -> None:
        if isinstance(config_filepath_or_file, str):
            with open(config_filepath_or_file, "w", encoding="utf-8") as config_file:
                dump_config_as_yaml(EXAMPLE_CONFIG, config_file)
        else:
            config_file = config_filepath_or_file
            dump_config_as_yaml(EXAMPLE_CONFIG, config_file)

    def __init__(self, config_filepath: str = DEFAULT_CONFIG_FILEPATH) -> None:
        self._config_filepath = config_filepath
        self.read_config()

    def write(self, config_filepath_or_file: Union[str, TextIO]) -> None:
        if isinstance(config_filepath_or_file, str):
            with open(config_filepath_or_file, "w", encoding="utf-8") as config_file:
                dump_config_as_yaml(self._config_dict, config_file)
        else:
            config_file = config_filepath_or_file
            dump_config_as_yaml(self._config_dict, config_file)

    def read_config(self, config_filepath: Optional[str] = None) -> None:
        self._config_dict = deepcopy(DEFAULT_CONFIG)
        validator = Validator(CONFIG_SCHEMA)
        if config_filepath is not None:
            self._config_filepath = config_filepath
        with open(os.path.abspath(os.path.expanduser(self._config_filepath)), "r") as f:
            if not validator.validate(yaml.safe_load(f)):
                raise ConfigValidationFailedError(self._config_filepath, validator.errors)
            normalized_config_dict = validator.document
            recursive_update(self._config_dict, normalized_config_dict)

    @staticmethod
    def _validate(config_dict: Dict[str, Any], config_filepath: Optional[str] = None) -> Dict[str, Any]:
        validator = Validator(CONFIG_SCHEMA)
        if not validator.validate(config_dict):
            raise ConfigValidationFailedError(config_filepath, validator.errors)
        return cast(Dict[str, Any], validator.document)

    def __getitem__(self, item: str) -> Any:
        return self._config_dict[item]


_config: Optional[Config] = None


def config(config_filepath: str = DEFAULT_CONFIG_FILEPATH) -> Config:
    global _config

    if _config is None:
        _config = Config(config_filepath)
    return _config
