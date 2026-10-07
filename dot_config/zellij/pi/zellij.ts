import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { randomUUID } from "node:crypto";
import { homedir } from "node:os";
import { join } from "node:path";

const run = promisify(execFile);
const helper = join(homedir(), ".config/zellij/bin/zellij-ws");
const owner = randomUUID();
const pane = process.env.ZELLIJ_PANE_ID;
const active = Boolean(process.env.ZELLIJ && process.env.ZELLIJ_SESSION_NAME && pane !== undefined);

export default function (pi: ExtensionAPI) {
	if (!active) return; // No commands, tools, events or processes in tmux/plain terminals.
	let outcome: "done" | "error" | "idle" = "done";
	let queue = Promise.resolve();
	let warned = false;
	let lastPrompt = "";
	const excerpt = (content: any): string => (typeof content === "string" ? content :
		Array.isArray(content) ? content.filter(b => b.type === "text").map(b => b.text).join(" ") : "")
		.replace(/[\x00-\x1f\x7f-\x9f]/g, " ").replace(/\s+/g, " ").trim().slice(0, 240);
	function restorePrompt(ctx: any) {
		const entry = [...(ctx.sessionManager?.getBranch?.() || [])].reverse()
			.find(e => e.type === "message" && e.message.role === "user");
		lastPrompt = excerpt(entry?.message.content);
	}

	async function invoke(args: string[]): Promise<string> {
		const result = await run(helper, args, { timeout: 15000, maxBuffer: 1024 * 1024 });
		return result.stdout.trim();
	}
	function publish(state: string, ctx: any, label?: string): Promise<void> {
		// Capture session-bound values before queued work can outlive its context.
		const prompt = lastPrompt;
		const sessionFile = ctx.sessionManager?.getSessionFile();
		// Serialize events so slow helper calls cannot overwrite newer state.
		queue = queue.then(async () => {
			try {
				await invoke(["event", state, "--pane", pane!, "--owner", owner,
					"--pid", String(process.pid), ...(label === undefined ? [] : [`--label=${label}`]),
					`--last-prompt=${prompt}`,
					...(sessionFile ? [`--session-file=${sessionFile}`] : []),
					...(process.env.ZELLIJ_RESTORE_TOKEN ? [`--restore-token=${process.env.ZELLIJ_RESTORE_TOKEN}`] : [])]);
			} catch (e) {
				if (!warned) {
					warned = true;
					ctx.ui.notify(`Zellij attention unavailable: ${String(e)}`, "warning");
				}
			}
		});
		return queue;
	}
	pi.on("session_start", async (_event, ctx) => {
		outcome = "done";
		restorePrompt(ctx);
		await publish("start", ctx, pi.getSessionName() || "pi");
	});
	pi.on("session_info_changed", async (event, ctx) => publish("label", ctx, event.name || "pi"));
	pi.on("session_switch", async (_event, ctx) => {
		restorePrompt(ctx);
		await publish("start", ctx, pi.getSessionName() || "pi");
	});
	for (const name of ["session_fork", "session_tree"] as const) pi.on(name, async (_event, ctx) => {
		restorePrompt(ctx);
		await publish("label", ctx, pi.getSessionName() || "pi");
	});
	pi.on("message_end", async (event, ctx) => {
		if (event.message.role !== "user") return;
		lastPrompt = excerpt(event.message.content);
		await publish("label", ctx);
	});
	pi.on("agent_start", async (_event, ctx) => {
		outcome = "done";
		await publish("working", ctx);
	});
	pi.on("ui_prompt_start", async (_event, ctx) => publish("asking", ctx));
	pi.on("ui_prompt_end", async (_event, ctx) => publish(ctx.isIdle() ? "idle" : "working", ctx));
	pi.on("agent_end", async (event) => {
		const last = [...event.messages].reverse().find(m => m.role === "assistant") as
			{ errorMessage?: string; stopReason?: string } | undefined;
		outcome = last?.stopReason === "aborted" ? "idle" :
			(last?.errorMessage || last?.stopReason === "error") ? "error" : "done";
		// Do not mark done here: retries/compaction/queued work can follow.
	});
	pi.on("agent_settled", async (_event, ctx) => {
		if (ctx.isIdle()) await publish(outcome, ctx);
	});
	pi.on("session_shutdown", async (_event, ctx) => publish("shutdown", ctx));

	async function picker(all = false): Promise<string> {
		return invoke(["popup", all ? "fleet" : "attention"]);
	}
	pi.registerCommand("znote", {
		description: "Set the shared task name for this Zellij tab; empty resets to shell",
		handler: async (args, ctx) => {
			try { ctx.ui.notify(await invoke(["note", "--", args]), "info"); }
			catch (e) { ctx.ui.notify(String(e), "error"); }
		},
	});
	for (const [name, all] of [["zattention", false], ["zfleet", true]] as const) {
		pi.registerCommand(name, {
			description: all ? "Pick any Zellij terminal pane" : "Jump to a Pi agent needing attention",
			handler: async (_args, ctx) => {
				try { await picker(all); } catch (e) { ctx.ui.notify(String(e), "error"); }
			},
		});
	}
	for (const [name, kind, direction] of [["zv", "split", "right"], ["zh", "split", "down"], ["zpi", "tab", "right"]] as const) {
		pi.registerCommand(name, {
			description: `Open Pi in a ${kind === "tab" ? "new tab" : direction + " split"}; optional initial prompt`,
			handler: async (args, ctx) => {
				try {
					ctx.ui.notify(await invoke(["open", "--kind", kind, "--direction", direction,
						"--cwd", ctx.cwd, "--name", "pi", "--", "pi", ...(args.trim() ? ["--", args] : [])]), "info");
				} catch (e) { ctx.ui.notify(String(e), "error"); }
			},
		});
	}
	pi.registerCommand("ztool", {
		description: "Run an explicit shell command in a right Zellij split (same directory)",
		handler: async (args, ctx) => {
			if (!args.trim()) { ctx.ui.notify("Usage: /ztool <shell command>", "error"); return; }
			try { ctx.ui.notify(await invoke(["open", "--cwd", ctx.cwd, `--name=${args.slice(0, 40)}`, "--", "/bin/sh", "-c", args]), "info"); }
			catch (e) { ctx.ui.notify(String(e), "error"); }
		},
	});
	pi.registerTool({
		name: "zellij_workspace",
		label: "Zellij workspace",
		description: "List Zellij panes/agent states, set task notes, focus a pane, or open a user-requested command/agent. Never start agents or commands proactively. Does not inspect transcripts or close panes. Stay in the current session; new tabs append without rearranging existing ones.",
		parameters: Type.Object({
			action: Type.Union([Type.Literal("list"), Type.Literal("attention"), Type.Literal("note"), Type.Literal("focus"), Type.Literal("open"), Type.Literal("workspace")]),
			workspace: Type.Optional(Type.String()),
			group: Type.Optional(Type.String()),
			command: Type.Optional(Type.Array(Type.String())),
			cwd: Type.Optional(Type.String()),
			note: Type.Optional(Type.String()),
			pane: Type.Optional(Type.String()),
			name: Type.Optional(Type.String()),
			kind: Type.Optional(Type.Union([Type.Literal("split"), Type.Literal("tab")])),
			direction: Type.Optional(Type.Union([Type.Literal("right"), Type.Literal("down")])),
			focus: Type.Optional(Type.Boolean()),
		}),
		async execute(_id, params, _signal, _update, ctx) {
			let args: string[];
			switch (params.action) {
				case "workspace":
					if (!params.workspace) throw new Error("workspace is required");
					args = ["workspace", params.workspace, "--dir", params.cwd || ctx.cwd,
						...(params.group ? [`--group=${params.group}`] : []), ...(params.focus ? ["--focus"] : [])]; break;
				case "list": args = ["list"]; break;
				case "attention": args = ["list", "--attention"]; break;
				case "note":
					if (params.note === undefined) throw new Error("note is required (empty clears)");
					args = ["note", ...(params.pane ? ["--pane", params.pane] : []), "--", params.note]; break;
				case "focus":
					if (!params.pane) throw new Error("pane is required");
					args = ["focus", params.pane]; break;
				case "open":
					if (!params.command?.length) throw new Error("command argv is required");
					args = ["open", "--kind", params.kind || "split", "--direction", params.direction || "right",
						"--cwd", params.cwd || ctx.cwd, ...(params.workspace ? [`--in=${params.workspace}`] : []), ...(params.name ? [`--name=${params.name}`] : []),
						...(params.note ? [`--note=${params.note}`] : []), ...(params.focus ? ["--focus"] : []), "--", ...params.command]; break;
			}
			if (params.workspace && (params.action === "note" || params.action === "focus")) {
				args = [`--session=${params.workspace}`, ...args];
			}
			const text = await invoke(args);
			return { content: [{ type: "text", text }], details: {} };
		},
	});
}
