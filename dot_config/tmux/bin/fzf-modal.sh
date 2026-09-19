# Shared vim-style modal mode for the fzf pickers. Source this file.
#
# Normal mode: letters and digits are bound to fzf actions (j/k move, g/G,
# q quit, plus per-picker extras) or to `ignore`, so typing never filters.
# `/` clears the query and unbinds those keys so typing filters live.
# Esc in search mode rebinds them and keeps the current filter and cursor;
# Esc in normal mode quits. Symbols are left unbound: in normal mode they
# land in the query harmlessly and `/` clears them.
#
#   FZF_MODAL              base options (use "${FZF_MODAL[@]}")
#   fzf_modal_normal P [key:action ...]   bind string for normal mode
#   fzf_modal_search P                    bind string for / and Esc
#   P is the normal-mode prompt to restore.

FZF_MODAL=(--bind 'ctrl-d:half-page-down,ctrl-u:half-page-up')

_fzf_modal_keys() {
    local c
    for c in {0..9} {a..z} {A..Z}; do printf '%s\n' "$c"; done
}
FZF_MODAL_KEYLIST=$(_fzf_modal_keys | paste -sd,)

fzf_modal_normal() {
    local prompt="$1"; shift
    local -A action=([j]=down [k]=up [g]=first [G]=last [q]=abort)
    local pair
    for pair in "$@"; do action["${pair%%:*}"]="${pair#*:}"; done
    local out="" c
    while read -r c; do
        out+="${out:+,}$c:${action[$c]:-ignore}"
    done < <(_fzf_modal_keys)
    printf '%s' "$out"
}

fzf_modal_search() {
    local prompt="$1"
    printf '%s' "/:clear-query+change-prompt(/ )+unbind[$FZF_MODAL_KEYLIST],esc:transform:[ \"\$FZF_PROMPT\" = \"/ \" ] && echo \"change-prompt($prompt)+rebind[$FZF_MODAL_KEYLIST]\" || echo abort"
}
