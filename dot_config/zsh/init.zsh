# Enable completion. The dump directory must exist or the cache can never
# be written and completions are rebuilt on every shell (~300ms). Skip the
# insecure-directory scan when the dump is younger than a day.
autoload -Uz compinit
[[ -d ~/.cache/zsh ]] || mkdir -p ~/.cache/zsh
if [[ -n ~/.cache/zsh/zcompdump(#qN.mh-24) ]]; then
    compinit -C -d ~/.cache/zsh/zcompdump
else
    compinit -d ~/.cache/zsh/zcompdump
fi

# Plugins
. "./plugins.zsh"

# Export vars
. "./config.zsh"

# Shell Prompt
. "./prompt.zsh"


. "./utils.zsh"
. "./alias.zsh"

# Run fastfetch on every new shell (gotta flex)
fastfetch
