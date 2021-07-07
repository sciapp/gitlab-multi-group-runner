# GitLab Multi Group Runner

## Overview

Until the creation of this README (July 2021), GitLab lacks the feature of assigning a CI runner to multiple groups (see
[issue #23722 in the GitLab code repository](https://gitlab.com/gitlab-org/gitlab/-/issues/23722)). This project
circumvents this limitation by assigning runners to all projects of given groups with the GitLab API.

This tool can be used as a command line program from any machine which has network access to your GitLab instance.
Alternatively, you setup it as a custom GitLab runner which is triggered from a configuration repository.

This tool needs administrator access to your GitLab instance.

## Installation

### Install as a standalone command line tool

`gitlab-multi-group-runner` is available on PyPI for Python 3.5+ and can be installed with `pip`:

```bash
python3 -m pip install gitlab-multi-group-runner
```

`pip` will create an executable `gitlab-multi-group-runner`.

If you use Arch Linux or one of its derivatives, you can also install `gitlab-multi-group-runner` from the
[AUR](https://aur.archlinux.org/packages/python-gitlab-multi-group-runner/):

```bash
yay -S python-gitlab-multi-group-runner
```

You also find self-contained executables for 64-bit Linux distributions and macOS High Sierra and newer on the [releases
page](https://github.com/sciapp/gitlab-multi-group-runner/releases/latest). They are created with
[PyInstaller](http://www.pyinstaller.org) and only require glibc >= 2.17 on Linux (should be fine on any recent Linux
system).

### Install as a custom GitLab runner

This is the recommended setup.

You can follow these steps:

- Create a new empty GitLab repository which will contain the configuration file.
- Install GitLab runner on a dedicated host as described in the [GitLab runner
  documentation](https://docs.gitlab.com/runner/install/) (of course a virtual machine or an LXC is also sufficient).
- Go to the webpage of your fresh GitLab repository and navigate to *Settings* -> *CI/CD* -> *Runners* and copy the
  *registration token* from the *Specific runners* section. Disable *Shared runners*.
- Run the `register` command on the GitLab runner host

  ```bash
  gitlab-runner register
  ```

  and enter these values:

  | Field               | Value                                    |
  | ------------------- | ---------------------------------------- |
  | GitLab instance URL | *URL to your GitLab instance*            |
  | Registration token  | *Copied before*                          |
  | Description         | `multi-group-configuration-runner`       |
  | Tags                | *Empty*                                  |
  | Executor            | `custom`                                 |

- Clone the GitHub repository <https://github.com/sciapp/gitlab-multi-group-runner> onto your GitLab runner host and run
  the installation:

  ```bash
  git clone https://github.com/sciapp/gitlab-multi-group-runner
  cd gitlab-multi-group-runner
  make install
  ```

  By default, the `make install` command will install a custom GitLab runner driver to `/opt/multi-group-runner-driver`.
  You can pass `PREFIX` to the make command to change the installation destination.

- Edit `/etc/gitlab-runner/config.toml`:

  - Configure the `builds_dir` and `cache_dir` settings:

    ```toml
    [[runners]]
      builds_dir = "/home/gitlab-runner/builds"
      cache_dir = "/home/gitlab-runner/cache"
    ```

  - Configure the `run` stage:

    ```toml
    [runners.custom]
      run_exec = "/opt/multi-group-runner-driver/bin/run_stage"
      run_args = [ "-f", "/opt/multi-group-runner-driver/etc/gitlab_multi_group_runnerrc.yml" ]
    ```

- Create a configuration file `/opt/multi-group-runner-driver/etc/gitlab_multi_group_runnerrc.yml`. See the section
  [Configuration](#configuration) for more details.

- Restart the GitLab runner service:

  ```bash
  sudo systemctl restart gitlab-runner
  ```

- Create a configuration file `multi-group-runner-config.yml` in the top level directory of the GitLab repository. See
  [Configuration](#configuration) for more details.

- Create a CI configuration file `.gitlab-ci.yml` next to `multi-group-runner-config.yml` with the content:

  ```yaml
  stages:
  - apply-config

  apply-config:
    stage: apply-config
    script: noop
  ```

  This minimal configuration file is needed to trigger a CI pipeline when new commits are pushed to the repository and
  to activate the custom CI runner.

- (Optional) Go to the webpage of your fresh GitLab repository and navigate to *CI/CD* -> *Schedules* and create a
  repeating event to configure new projects automatically in a defined interval.

When the CI pipeline is triggered, the configuration file in the repository is read and the runner will reconfigure the
runners in the configured groups and projects. You should see something like

```text
Running on multi-group-configuration-runner...
[INFO] Disable shared runners in project "mygroup/myproject"
[INFO] Enable runner "intel-docker", (id: 10, tags: ["docker", "intel"]) in project "mygroup/myproject"
[...]
```

in your CI job log.

## Configuration

`gitlab-multi-group-runner` uses two configuration files:

- The first configuration file must be located on the same machine as the executable `gitlab-multi-group-runner`. It
  contains parameters which are needed for the GitLab API access and specifies which runners and groups are allowed to
  be configured and which configuration repositories are accepted (see next step). This is an example configuration file
  (can also be printed with `gitlab-multi-group-runner --print-example-config`):

  ```yaml
  general:
    disable_shared_runners: true
  gitlab:
    auth_token: xxxxxxxxxxxxxxxxxxxx
    url: https://mygitlab.com
  runners:
  - allowed_projects_rules:
      one_member_of:
      - my-group-name
      - my-user-name
    ids:
    - 1
    - 3
    config_repo:
      branch: master
      path: administration/my-multi-group-runners
  ```

  Some notes:

  - `disable_shared_runners` specifies if shared runners will be disabled in **all** repositories which are reconfigured
    by this tool. Set it to `false`, to not touch shared runners.

  - The `auth_token` must be a token for the administrator account with `api` and `read_repository` access. Login as
    `root` and go to *Preferences* -> *Access Tokens* to generate a new token.

  - `allowed_projects_rules` is a set of rules to identify projects which are allowed to be configured. Currently, only
    the rule `one_member_of` is supported. The value is a list of groups and users from which it least one user must be
    a member of the project which shall be configured.

    **Example**: If `foo` is given, then all projects in the group `foo` are allowed to be configured. If another
    project `bar` has a member of group `foo`, the project `bar` can be configured as well.

  - `ids` is a list of runner ids which are allowed to be assigned to the projects defined by `allowed_projects_rules`.
    The *Admin Area* of your GitLab instance contains a *Runners* section which lists all runners and their ids.

    **Important**: Only specific runners can be used (so group runners must be re-registered as specific runners first).
    It does not matter if specific runners are locked or not.

  - `config_repo` specifies the GitLab repository which contains the second configuration file. The configuration
    repository specifies concretely which runners are assigned to which groups and projects.

  - Note that `allowed_projects_rules`, `ids` and `config_repo` form a list item of the `runners` list. You can specify
    as much triples as you need to describe which configuration repositories can configure which combinations of
    runners, groups and projects.

- As noted before, the second configuration part is located in a Git repository on your GitLab instance. It must be
  located in the top level root and must be named `multi-group-runner-config.yml`. This is an example configuration (can
  also be printed with `gitlab-multi-group-runner --print-example-repo-config`):

  ```yaml
  runners:
  - groups_and_projects:
    - mygroup
    - myusername/myproject
    ids:
    - 1
    - 3
  ```

  The `runners` section is a list of group/project and runner combinations. It configures which runners will be assigned
  to which concrete projects and groups.

## Usage

### Usage of the standalone command line tool

Run `gitlab-multi-group-runner` with a local configuration file and a configuration repository path:

```bash
gitlab-multi-group-runner -f my_config.yml administration/my-multi-group-runners
```

`gitlab-multi-group-runner` will read both configuration files, check if the settings in
`administration/my-multi-group-runners` are allowed and make the appropriate GitLab API calls to add the runners to the
given projects.

You can run with the `--all` parameter to fetch all configuration repositories which are defined in `my_config.yml`.

### Usage as a custom GitLab runner

Push a new commit to your configuration repository and wait for the CI pipeline to complete. That's it!

## Contributing

Please open [an issue on GitHub](https://github.com/sciapp/gitlab-multi-group-runner/issues/new) if you experience bugs
or miss features. Please consider to send a pull request if you can spend time on fixing the issue yourself. This
project uses [pre-commit](https://pre-commit.com) to ensure code quality and a consistent code style. Run

```bash
make git-hooks-install
```

to install all linters as Git hooks in your local clone of `gitlab-multi-group-runner`.
