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
        init = function()
            -- Add shortened commands for Competitest.
            -- "CP" -> CompetiTest run
            -- "CP problem" -> CompetiTest receive problem
            -- "CP contest" -> CompetiTest receive contest

            vim.cmd([[
                "Call the appropriate CompetiTest command
                function! s:CompetiTestFunction(arg) abort
                if a:arg == ""
                    " Create bin folder if not existing
                    if !isdirectory("./bin")
                        call mkdir("./bin")
                    endif

                    execute "CompetiTest run"
                else
                    " Create .gitignore to hide input and binary files in telescope 🔭
                    if !filereadable(".gitignore")
                    call writefile(["testcases\nbin"], ".gitignore")
                endif

                    execute 'CompetiTest receive ' . a:arg
                endif
            endfunction

            "Tab completion of the command with 'contest' or 'problem'
            function! s:CompetiTestComplete(...) abort
                let l:options = ['problem', 'contest']
                return join(l:options, "\n")
            endfunction

            "The actual command
            command! -bar -nargs=? -complete=custom,s:CompetiTestComplete CP call s:CompetiTestFunction(<q-args>)
        ]])

        end
    }
}
