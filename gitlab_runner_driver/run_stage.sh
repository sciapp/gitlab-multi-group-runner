#!/bin/bash

if [[ -z "${BUILD_FAILURE_EXIT_CODE}" ]]; then
    >&2 echo "This script can only be run as a GitLab custom runner driver."
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


main () {
    declare -a args
    declare -a gitlab_multi_group_runner_args
    local runner_script
    local runner_stage

    args=( "$@" )
    gitlab_multi_group_runner_args=( "${args[@]:0:$(( ${#args[@]} - 2 ))}" )
    runner_script="${args[-2]}"
    runner_stage="${args[-1]}"

    case "${runner_stage}" in
        prepare_script)
            # Run the script which was prepared by GitLab itself:
            bash "${runner_script}" || return "${BUILD_FAILURE_EXIT_CODE}"
            ;;
        build_script|step_script)
            CLICOLOR_FORCE=1 \
            TERM=ansi \
            "${SCRIPT_DIR}/gitlab-multi-group-runner" \
                -f "${SCRIPT_DIR}/../etc/gitlab_multi_group_runnerrc.yml" \
                "${gitlab_multi_group_runner_args[@]}" \
                "${CUSTOM_ENV_CI_PROJECT_PATH}" || return "${BUILD_FAILURE_EXIT_CODE}"
            ;;
        *)
            # Simply ignore all other run stages
            return 0
            ;;
    esac
}

main "$@"
