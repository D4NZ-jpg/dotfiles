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
        "xeluxee/competitest.nvim",
        dependencies = { "MunifTanjim/nui.nvim" },
        opts = {
            template_file = "~/dev/cp/Settings/template.cpp",
            testcases_directory = "testcases",
            testcases_input_file_format = "$(FNOEXT).in$(TCNUM)",
            testcases_output_file_format = "$(FNOEXT).out$(TCNUM)",
            save_current_file = true,
            evaluate_template_modifiers = true,
            received_files_extension = "cpp",
            received_problems_prompt_path = false,
            received_contests_prompt_directory = false,
            received_contests_prompt_extension = false,
            date_format = "%d-%m-%Y %H:%M:%S",
            run_command = {
                cpp = {
                    exec = "./bin/$(FNOEXT)"
                }
            },
            compile_command = {
                cpp = { exec = "g++", args = { "-g", "-DDEBUG", "$(FNAME)", "-o", "./bin/$(FNOEXT)" } }
            }
        },
        cmd = "CompetiTest",
    }
}
