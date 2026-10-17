# Exports
export EDITOR='nvim'
export WLR_NO_HARDWARE_CURSORS=1

# Commands prefixed with a space stay out of Deja's local suggestion database.
setopt HIST_IGNORE_SPACE

# Keep predictive text legible but subordinate to typed input on the charcoal theme.
export DEJA_HIGHLIGHT_STYLE='fg=#827c70'
# Kitty reports Ctrl+Right as CSI 1;5C; use it for word-wise acceptance.
export DEJA_WORD_ACCEPT_KEY=$'\e[1;5C'
