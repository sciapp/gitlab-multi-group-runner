INSTALL = install
PREFIX = /opt/multi-group-runner-driver

BIN_FILES := run_stage.sh


install:
	@$(INSTALL) -d "$(PREFIX)/bin"
	@for filename in $(BIN_FILES); do \
		$(INSTALL) -v -m 0555 "$${filename}" "$(PREFIX)/bin/$$(basename $${filename%.*})"; \
	done
	@echo
	@echo "Run \`gitlab-runner register\`, set executor type \`custom\`"
	@echo "and set the run configuration in \`/etc/gitlab-runner/config.toml\`:"
	@echo
	@echo "  [runners.custom]"
	@echo "    run_exec = \"$(PREFIX)/bin/run_stage\""
	@echo "    run_args = [ \"-f\", \"$(PREFIX)/etc/gitlab_multi_group_runnerrc.yml\" ]"
	@echo


.PHONY: install
