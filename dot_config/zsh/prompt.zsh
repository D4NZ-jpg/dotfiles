# Prompt Config

bindkey -v # Vim mode
bindkey -M viins 'kk' vi-cmd-mode # Escape with 'kk'

eval "$(starship init zsh)"

# Collapse only a finished command line. Do not recursively edit or accept input.
# Native Zsh color escapes have correct display widths (unlike raw ANSI output).
autoload -Uz add-zsh-hook add-zle-hook-widget

_dan_transient_line_finish() {
  [[ $CONTEXT == start ]] || return 0
  typeset -g _dan_full_prompt=$PROMPT
  typeset -g _dan_full_rprompt=$RPROMPT
  typeset -g _dan_transient_active=1
  PROMPT=$'\n%F{blue}󰍟%f '
  RPROMPT='%B%F{blue}%D{%H:%M}%f%b '
  zle .reset-prompt
}

_dan_transient_restore() {
  local previous_status=$?
  if [[ ${_dan_transient_active:-0} == 1 ]]; then
    PROMPT=$_dan_full_prompt
    RPROMPT=$_dan_full_rprompt
    unset _dan_transient_active _dan_full_prompt _dan_full_rprompt
  fi
  return $previous_status
}

add-zle-hook-widget line-finish _dan_transient_line_finish
# Run before Starship's precmd hook and preserve the previous command's status.
precmd_functions=(_dan_transient_restore ${precmd_functions:#_dan_transient_restore})
