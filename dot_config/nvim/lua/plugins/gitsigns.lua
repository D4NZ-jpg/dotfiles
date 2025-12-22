return {
    "lewis6991/gitsigns.nvim",
    event = "BufReadPre",
    keys = {
        { "<leader>gd", "<cmd>Gitsigns diffthis<cr>", desc = "Git Diff" },
        { "<leader>gh", "<cmd>Gitsigns preview_hunk<cr>", desc = "Preview Hunk" },
        { "<leader>gs", "<cmd>Gitsigns stage_hunk<cr>", desc = "Stage Hunk" },
        { "<leader>gu", "<cmd>Gitsigns undo_stage_hunk<cr>", desc = "Undo Stage Hunk" },
        { "<leader>gr", "<cmd>Gitsigns reset_hunk<cr>", desc = "Reset Hunk" },
        { "<leader>gb", "<cmd>Gitsigns blame_line<cr>", desc = "Blame Line" },
    },
    opts = {
        current_line_blame = true,
    }
}
