return {
	"Fildo7525/pretty_hover",
	event = "LspAttach",
	opts = {},
    keys = {
        {
            "K",
            function()
                require("pretty_hover").hover()
            end,
            desc = "Pretty Hover (open)",
        },
        {
            "q",
            function()
                require("pretty_hover").close()
            end,
            desc = "Pretty Hover (close)",
        }
    }
}
