# Prompt Config

bindkey -v # Vim mode
bindkey -M viins 'kk' vi-cmd-mode # Escape with 'kk'

## Transient prompt

starship_transient_prompt_func() {
  starship module character
}

starship_transient_rprompt_func() {
  starship module time
}

### Enable transient prompt
zle-line-init() {
  emulate -L zsh
  [[ $CONTEXT == start ]] || return 0

  while true; do
    zle .recursive-edit

    local -i ret=$?

    [[ $ret == 0 && $KEYS == $'\4' ]] || break
    [[ -o ignore_eof ]] || exit 0

  done

  local saved_prompt=$PROMPT
  local saved_rprompt=$RPROMPT

  PROMPT=$'\n$(starship_transient_prompt_func) '
  RPROMPT='$(starship_transient_rprompt_func)'

  zle .reset-prompt

  PROMPT=$saved_prompt
  RPROMPT=$saved_rprompt

  if ((ret)); then
    zle .send-break
  else
    zle .accept-line
  fi


  return ret
}

zle -N zle-line-init

# Evaluate

eval "$(starship init zsh)"
