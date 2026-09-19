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

# tmux workspace note for the current window (shown in the status line)
note() {
  [ -z "$TMUX" ] && { echo "not inside tmux"; return 1; }
  if [ $# -eq 0 ]; then tmux show -wv @note 2>/dev/null; else tmux set -w @note "$*"; fi
}
