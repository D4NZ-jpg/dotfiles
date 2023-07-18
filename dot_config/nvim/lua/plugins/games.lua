return {
    -- minesweeper
    {
        "seandewar/nvimesweeper",
        cmd = "Nvimesweeper"
    },

    -- Blacjack
    {
        "alanfortlink/blackjack.nvim",
        cmd = "BlackJackNewGame"
    },

    -- Tetris
    {
        "alec-gibson/nvim-tetris",
        cmd = "Tetris"
    },

    -- Cellular-automaton
    {
        "Eandrju/cellular-automaton.nvim",
        cmd = "CellularAutomaton"
    },

    -- Competitive programming
    {
        "D4NZ-jpg/competitest.nvim",
        dependencies = { "MunifTanjim/nui.nvim" },
        branch = "patches",
        opts = {
            template_file = "~/dev/cp/Settings/template.cpp",
            head_comment =
            "// Problem: $(NAME)\n// Contest: $(GROUP)\n// URL: $(URL)\n// Memory Limit: $(MEMLIM) MB\n// Time Limit: $(TIMELIM) ms\n// Start: $(TIME)",
            time_format = "%d-%m-%Y %H:%M:%S",
            testcases_directory = "testcases",
            testcases_use_single_file = true,
            save_current_file = true,
            run_command = {
                cpp = {
                    exec = "./bin/$(FNOEXT)"
                }
            },
            compile_command = {
                cpp = { exec = "g++", args = { "-g", "$(FNAME)", "-o", "./bin/$(FNOEXT)" } }
            }
        },
        cmd = { "CompetiTestReceive", "CompetiTestRun" },
    }
}
