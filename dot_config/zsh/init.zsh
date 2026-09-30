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

# Export vars and privacy settings must exist before plugins initialize.
. "./config.zsh"

# Shell prompt also selects the vi keymap before suggestion widgets bind keys.
. "./prompt.zsh"

. "./utils.zsh"
. "./alias.zsh"

# ZLE integrations load last; syntax highlighting requires this ordering.
. "./plugins.zsh"

# Run fastfetch on every new shell (gotta flex)
fastfetch
