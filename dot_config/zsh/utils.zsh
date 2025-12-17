# Prevent system shutdown during sensitive commands (idle not affected)
prevent_shutdown(){
    # Check if command and arguments are provided
    if [ $# -eq 0 ]; then
        echo "No command provided"
        return 1
    fi

    # Extract the command and its arguments
    cmd=$1
    shift

    description="Prevent shutdown when runnning $cmd"

    systemd-inhibit --who="$cmd" --what=sleep:shutdown:handle-power-key:handle-suspend-key:handle-hibernate-key:handle-lid-switch --mode=block --why="$description" "$cmd" "$@"
}
