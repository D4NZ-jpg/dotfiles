#!/bin/bash

# Ensure task is installed
if ! command -v task &> /dev/null; then
    printf "task could not be found, please install it.\n" >&2
    exit 1
fi

complete() {
    local id="$1"

    id=$(echo "$id" | tr -d '\n')
    if [[ -z "$id" ]]; then
        return 0 
    fi


    local dependencies=$(task _get $id.depends)

    if [[ -n "$dependencies" ]]; then
        readarray -td, deps <<<"$dependencies,"
        for dep in "${deps[@]}"; do
            [ -z "$dep" ] && continue
            complete "$dep" &> /dev/null
        done
    fi

    task rc.bulk=0 rc.confirmation=off "$id" done 
}


confirm_operation() {
    local id=$1
    local confirm

    printf "Are you sure you want to set as done task with id %s? (y/N): " "$id"
    read -r confirm
    if [[ $confirm != [yY] ]]; then
        printf "Operation aborted.\n" >&2
        return 1
    fi
}

main() {
    set -o pipefail
    local id="$1"

    if [[ -z "$id" ]]; then
        printf "Usage: $0 <task_id>\n" >&2
        return 1
    fi

    # Ensure the given task exists
    if ! task _get $id.uuid &>/dev/null; then
        printf "Task with id %s does not exist.\n" "$id" >&2
        return 1
    fi


    # Confirm before deletion
    if ! confirm_operation "$id"; then
        return 1
    fi

    complete "$id" &> /dev/null
}

main "$@"
