return {
    "zbirenbaum/copilot.lua",
    dependencies = { "copilotlsp-nvim/copilot-lsp" },
    opts = {
        suggestion = {
            enabled = true,
            auto_trigger = true,
            keymap = {
                accept = "<M-y>",
                next = "<M-]>",
                prev = "<M-[>",
                dismiss = "<M-n>",
                accept_word = false,
                accept_line = false,
            },

        }
    },
    event = "InsertEnter",
    cmd = "Copilot"
}
