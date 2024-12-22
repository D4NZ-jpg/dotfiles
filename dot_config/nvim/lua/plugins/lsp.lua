return {
  -- LSP
  {
    'neovim/nvim-lspconfig',
    event = "InsertEnter",
    dependencies = {
      'saghen/blink.cmp',
      "williamboman/mason.nvim",
      "williamboman/mason-lspconfig.nvim",
    },


    opts = {
      servers = {
      }
    },

    config = function(_, opts)
      -- Format on save
      vim.api.nvim_create_autocmd('LspAttach', {
        callback = function(args)
          local client = vim.lsp.get_client_by_id(args.data.client_id)
          if not client then return end

          if client.supports_method('textDocument/formatting') then
            vim.api.nvim_create_autocmd('BufWritePre', {
              buffer = args.buf,
              callback = function()
                vim.lsp.buf.format({ bufnr = args.buf, id = client.id })
              end
            })
          end
        end,
      })


      require("mason").setup()
      require("mason-lspconfig").setup()

      -- Default handler
      local handlers = {
        function(server_name)
          local config = {
            capabilities = require('blink.cmp').get_lsp_capabilities()
          }
          require("lspconfig")[server_name].setup(config)
        end,
      }

      -- Set handler for each config in opts.server
      for server, config in pairs(opts.servers) do
        handlers[server] = function()
          config.capabilities = require('blink.cmp').get_lsp_capabilities(config.capabilities)
          require("lspconfig")[server].setup(config)
        end
      end

      require("mason-lspconfig").setup_handlers(handlers)

      -- Force LSP to start, when lazy loading
      vim.cmd([[LspStart]])
    end,
  },

  -- Completion
  {
    'saghen/blink.cmp',
    event = "InsertEnter",
    version = 'v0.x',
    dependencies = {
      'rafamadriz/friendly-snippets',
      'saghen/blink.compat',
      {
        'L3MON4D3/LuaSnip',
        version = 'v2.*',
        build = "make install_jsregexp",
        config = function()
          -- If in my competitive programming folder load special cp snippets
          local cwd = vim.fn.getcwd()
          if string.find(cwd, "/dev/cp/?") then
            require("luasnip.loaders.from_snipmate").lazy_load({
              paths = { "$HOME/dev/cp/snippets" }
            })
          else
            require("luasnip.loaders.from_snipmate").lazy_load()
          end
        end,
      }
    },
    opts = {
      keymap = { preset = 'default' },
      appearance = {
        use_nvim_cmp_as_default = true,
        nerd_font_variant = 'mono'
      },

      sources = {
        default = { 'lsp', 'path', 'luasnip', 'buffer' },
        providers = {
          luasnip = {
            name = 'Luasnip',
            module = 'blink.cmp.sources.luasnip',
            opts = {
              use_show_condition = true,
              show_autosnippets = true,
            },
          },
        },
      },

      signature = { enabled = true },
      snippets = {
        expand = function(snippet) require('luasnip').lsp_expand(snippet) end,
        active = function(filter)
          if filter and filter.direction then
            return require('luasnip').jumpable(filter.direction)
          end
          return require('luasnip').in_snippet()
        end,
        jump = function(direction) require('luasnip').jump(direction) end,
      },
    },
  },

  -- Copilot
  {
    "zbirenbaum/copilot.lua",
    event = "InsertEnter",
    cmd = "Copilot",
    build = ":Copilot auth",
    opts = {
      suggestion = {
        enabled = true,
        auto_trigger = true,
        hide_during_completion = true,
        keymap = {
          accept = "<M-y>",
          next = "<M-]>",
          prev = "<M-[>",
        },
      },
      panel = { enabled = false },
      filetypes = {
        markdown = true,
        help = true,
      },
    },
  },

  -- Flutter
  {
    'nvim-flutter/flutter-tools.nvim',
    dependencies = {
      'neovim/nvim-lspconfig',
      'nvim-lua/plenary.nvim',
      'stevearc/dressing.nvim', -- optional for vim.ui.select
    },
    config = true,
    ft = "dart"
  }
}
