alias yay='prevent_shutdown yay'
alias pacman='prevent_shutdown pacman'

alias lz='lazygit'
alias ..='cd ..'

alias ll='ls -lh'
alias la='ls -la'

# Eza alias
if (( $+commands[eza] )); then
    alias ls='eza --icons --group-directories-first'
    alias ll='eza -lh --git'
    alias la='eza -la'
fi

# Bat alias
if (( $+commands[bat] )); then
  alias cat='bat'
fi

# Zoxide
if (( $+commands[zoxide] )); then
  eval "$(zoxide init zsh)"
fi
