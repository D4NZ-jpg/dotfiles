return {
  {
    "epwalsh/pomo.nvim",
    version = "*",
    lazy = true,
    cmd = { "TimerStart", "TimerRepeat", "TimerSession" },
    opts = {
      sessions = {
        cp = {
          { name = "Competitive Programming", duration = "25m" }
        }
      }
    }
  }
}
