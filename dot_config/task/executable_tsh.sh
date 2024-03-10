#!/bin/bash

# Ensure task is installed
if ! command -v task &> /dev/null; then
    printf "task could not be found, please install it.\n" >&2
    exit 1
fi

count() {
    local id="$1"
    local count=1

    id=$(echo "$id" | tr -d '\n')
    if [[ -z "$id" ]]; then
        echo 0
        return
    fi

    local dependencies=$(task _get $id.depends)

    if [[ -n "$dependencies" ]]; then
        readarray -td, deps <<<"$dependencies,"
        for dep in "${deps[@]}"; do
            [ -z "$dep" ] && continue

            ((count += $(count "$dep")))
        done
    fi

    echo $count
}

update(){
    local id="$1"
    local order="$2"
    local total="$3"
    local unit="$4"

    id=$(echo "$id" | tr -d '\n')
    if [[ -z "$id" ]]; then
        echo "$((order - 1))"
        return
    fi


    # Calculate new due and schedule times based on total, order, and unit
    local due_time="$(task calc "now + ($total - $order)*$unit")"
    local schedule_time="$(task calc "now + ($total - $order - 1)*$unit")"

    # Update task with new due and schedule times
    if ! task "$id" modify due:"$due_time" schedule:"$schedule_time"; then
        printf "Failed to modify task for ID '%s'\n" "$id" >&2
        return 1
    fi

    local dependencies=$(task _get "$id.depends")
    if [[ -n "$dependencies" ]]; then
        readarray -td, deps <<<"$dependencies,"
        for dep in "${deps[@]}"; do
            [ -z "$dep" ] && continue
            ((order++))
            update "$dep" "$order" "$total" "$unit"
        done
    fi

    echo $((order))
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

    # Make sure task has due
    due_date=$(task _get "$id".due) || {
        printf "Failed to retrieve due date for task with id %s.\n" "$id" >&2
        return 1
    }

    if [[ -z "$due_date" ]]; then
        printf "Task with id %s does not have a due date.\n" "$id" >&2
        return 1
    fi

    local total
    total=$(count "$id")
    local unit="$(task calc \($(task _get $id.due) - now\)/$total)"
    update "$id" 0 $total "$unit" &> /dev/null
}

main "$@"
