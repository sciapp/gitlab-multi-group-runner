INSTALL = install
PRECOMMIT_VERSION=2.13.0
PRECOMMIT_URL=$\
	https://github.com/pre-commit/pre-commit/releases/download/$\
	v$(PRECOMMIT_VERSION)/pre-commit-$(PRECOMMIT_VERSION).pyz
PREFIX = /opt/multi-group-runner-driver

no_default:
	@echo "There is no default target. Please choose one of the following targets: git-hooks-install, install"
	@exit 1

git-hooks-install:
	@if ! command -v python3 >/dev/null 2>&1; then \
		>&2 echo "Please install Python 3 first."; \
		exit 1; \
	fi; \
	TMP_PRECOMMIT_DIR="$$(mktemp -d 2>/dev/null || mktemp -d -t 'tmp' 2>/dev/null)" && \
	curl -L -o "$${TMP_PRECOMMIT_DIR}/pre-commit.pyz" "$(PRECOMMIT_URL)" && \
	python3 "$${TMP_PRECOMMIT_DIR}/pre-commit.pyz" install && \
	python3 "$${TMP_PRECOMMIT_DIR}/pre-commit.pyz" install --hook-type commit-msg && \
	rm -rf "$${TMP_PRECOMMIT_DIR}"

install:
	@if ! command -v python3 >/dev/null 2>&1; then \
		>&2 echo "Please install Python 3 first."; \
		exit 1; \
	fi
	@if ! python3 -c 'import pip; import venv' >/dev/null 2>&1; then \
		>&2 echo "Please install Python3 pip and venv."; \
		exit 1; \
	fi
	@$(INSTALL) -d "$(PREFIX)/bin"
	@python3 -m venv "$(PREFIX)/python_env"
	@"$(PREFIX)/python_env/bin/pip" install wheel
	@"$(PREFIX)/python_env/bin/pip" install .
	@ln -s "../python_env/bin/gitlab-multi-group-runner" "$(PREFIX)/bin/"
	@$(MAKE) PREFIX="$(PREFIX)" -C gitlab_runner_driver
	@echo
	@echo "Example \`gitlab_multi_group_runnerrc.yml\`:"
	@"$(PREFIX)/bin/gitlab-multi-group-runner" --print-example-config
	@echo
	@echo "See https://github.com/sciapp/gitlab-multi-group-runner/blob/master/README.md for more details."


.PHONY: no_default git-hooks-install install
