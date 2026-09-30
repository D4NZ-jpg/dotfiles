# Predictive suggestions. The generated integration is refreshed by Deja after
# binary upgrades; the fallback only runs on a first install before it exists.
if [[ -r "$HOME/.local/share/deja/init.zsh" ]]; then
  source "$HOME/.local/share/deja/init.zsh"
elif (( $+commands[deja] )); then
  eval "$(deja init zsh)"
fi

# Generate .gitignore content from the Toptal API: `gi linux,node`.
function gi() {
  curl -fLw '\n' "https://www.toptal.com/developers/gitignore/api/${(j:,:)@}"
}

_gitignoreio_get_command_list() {
  curl -sfL https://www.toptal.com/developers/gitignore/api/list | tr ',' '\n'
}

_gitignoreio() {
  local -a commands
  compset -P '*,'
  commands=("${(@f)$(_gitignoreio_get_command_list)}")
  compadd -S '' -- "${commands[@]}"
}

compdef _gitignoreio gi

# Must be loaded after other ZLE integrations. Installed by setup/pkgs/pkgs.lst.
if [[ -r /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]]; then
  source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi
