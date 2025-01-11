function find_obsidian_dir(path)
  if vim.fn.isdirectory(path .. "/.obsidian") == 1 then
    return path
  end

  local parent = vim.fn.fnamemodify(path, ":h")
  if parent == path then
    return nil
  end
  return find_obsidian_dir(parent)
end

function parseDate(dateStr)
  local patterns = {
    -- YYYY-MM-DD
    { pattern = "(%d+)-(%d+)-(%d+)",   order = { "year", "month", "day" } },
    -- DD/MM/YYYY
    { pattern = "(%d+)/(%d+)/(%d+)",   order = { "day", "month", "year" } },
    -- MM.DD.YYYY
    { pattern = "(%d+)%.(%d+)%.(%d+)", order = { "month", "day", "year" } }
  }

  for _, format in ipairs(patterns) do
    local v1, v2, v3 = dateStr:match(format.pattern)
    if v1 then
      local values = { v1 = tonumber(v1), v2 = tonumber(v2), v3 = tonumber(v3) }
      local year = values[format.order[1] == "year" and "v1" or format.order[2] == "year" and "v2" or "v3"]
      local month = values[format.order[1] == "month" and "v1" or format.order[2] == "month" and "v2" or "v3"]
      local day = values[format.order[1] == "day" and "v1" or format.order[2] == "day" and "v2" or "v3"]

      -- Convert to a single comparable number (YYYYMMDD)
      return year * 10000 + month * 100 + day
    end
  end
  return nil -- If no pattern matches
end

return {
  {
    "D4NZ-jpg/obsidian.nvim",
    version = "*",
    dependencies = "nim-lua/plenary.nvim",
    event = { "VeryLazy", "VimEnter *.md" },

    -- Load only on Obsidian directories
    cond = function()
      local cwd = vim.fn.getcwd()
      return find_obsidian_dir(cwd) ~= nil
    end,

    keys = {
      {
        "<leader>ont",
        "<cmd>ObsidianNewFromTemplate<cr>",
        desc = "File from template"
      },
      { "<leader>onn", "<cmd>ObsidianNew<cr>",   desc = "File" },
      { "<leader>od",  "<cmd>ObsidianToday<cr>", desc = "Open daily note" },
    },

    config = function(_, opts)
      require('which-key').add({ "<leader>o", group = "obsidian.nvim" })
      require('which-key').add({ "<leader>on", group = "New..." })

      require("obsidian").setup(opts)
    end,
    opts = {
      notes_subdir = "inbox",
      workspaces = {
        {
          name = "dynamic",
          path = function()
            -- Find the lowest parent with a .obsidian directory
            return find_obsidian_dir(vim.fn.expand "%:p:h")
          end,
        },
      },
      completion = {
        nvim_cmp = false
      },
      daily_notes = {
        folder = "journal",
        date_format = "%Y/%m-%B/%d-%m-%Y",
        template = "daily",
      },
      note_id_func = function(title)
        return title:lower():gsub("%s+", "-")
      end,
      templates = {
        folder = ".settings/templates",
        date_format = "%d/%m/%Y",
        output_dir_key = "target_dir",
        substitutions = {
          lastDaily = function(client)
            local notes = client:find_notes("daily")

            -- Filter only daily notes and not today
            notes = vim.tbl_filter(function(note)
              if note.metadata == nil then
                vim.notify(vim.inspect(note))
              end
              return note.id ~= select(2, client:daily_note_path()) and note.metadata.type == "daily"
            end, notes)

            -- sort by date
            table.sort(notes, function(a, b) -- 2024-10-20
              return parseDate(a.metadata.date) < parseDate(b.metadata.date)
            end)

            return notes[#notes].id
          end,

          today = function()
            return os.date("%A, %B %d, %Y")
          end,

          tomorrow = function(client)
            return select(2, client:daily_note_path(os.time() + 24 * 60 * 60))
          end,

        },

      },
    },
  }
}
