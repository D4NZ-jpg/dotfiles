/**
 * Pi extension: publish this session to its tmux window.
 *
 * Window options written (read by the status line and `prefix g`/`G`):
 *   @auto-note   session title (pi-autoname or /name); a manual @note wins
 *   @pi-state    working | asking | done | error | idle
 *   @pi-since    epoch seconds of the last state change
 *   @pi-last     first line of pi's last message or the open prompt's title,
 *                shown in the attention and fleet lists
 *   @agent       1 while pi runs, so silence detection applies
 *   @pi-session  path of this session's file, so tmux-restore can bring back
 *                exactly this thread with `pi --session` (no -c/-r guessing)
 *
 * Also sends the desktop notification when pi needs you (a prompt, a finished
 * run, an error), with the real text instead of a screen capture. Only fires
 * when the window is not the one you are looking at.
 *
 * Loaded through a symlink from ~/.pi/agent/extensions; source of truth is
 * ~/.config/tmux/pi/tmux-note.ts (managed by chezmoi).
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile, execFileSync } from "node:child_process";

const pane = process.env.TMUX_PANE;
const inTmux = Boolean(process.env.TMUX && pane);

function opt(name: string, value: string): void {
	if (!inTmux) return;
	execFile("tmux", ["set", "-w", "-t", pane as string, name, value], () => {});
}

function setState(state: string): void {
	opt("@pi-state", state);
	opt("@pi-since", String(Math.floor(Date.now() / 1000)));
}

function clean(text: string | undefined, max: number): string {
	const t = (text ?? "").replace(/[`*_#>]/g, "").replace(/\s+/g, " ").trim();
	return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

/** Text of the last assistant message in a run, for the notification body. */
function lastText(messages: unknown[] | undefined): string {
	for (let i = (messages?.length ?? 0) - 1; i >= 0; i--) {
		const m = messages?.[i] as { role?: string; content?: unknown; errorMessage?: string };
		if (m?.role !== "assistant") continue;
		if (m.errorMessage) return m.errorMessage;
		const parts = Array.isArray(m.content) ? m.content : [];
		const text = parts
			.filter((p): p is { type: string; text: string } => (p as { type?: string })?.type === "text")
			.map((p) => p.text)
			.join(" ");
		if (text.trim()) return text;
	}
	return "";
}

/** Notify unless this window is the one on screen. Synchronous so it survives pi exiting right after. */
function notify(title: string, body: string, urgency: "normal" | "critical" = "normal"): void {
	if (!inTmux) return;
	try {
		const out = execFileSync("tmux", ["display", "-p", "-t", pane as string, "#{session_name}\t#{window_active}#{session_attached}\t#{@note}"], { encoding: "utf8" });
		const [session, flags, note] = out.replace(/\n$/, "").split("\t");
		if (flags === "11") return; // active window of an attached session: you can see it
		const where = [session, clean(note, 40) || clean(currentTitle, 40)].filter(Boolean).join(" · ");
		execFileSync("notify-send", ["-a", "pi", "-u", urgency, `${where} — ${title}`, body], { stdio: "ignore" });
	} catch {}
}

let currentTitle: string | undefined;

function setAutoNote(name: string | undefined): void {
	opt("@auto-note", (name ?? "").replace(/\s+/g, " ").trim().slice(0, 60));
}

export default function (pi: ExtensionAPI) {
	if (!inTmux) return;

	pi.on("session_start", async (_event, ctx) => {
		opt("@agent", "1");
		opt("@pi-session", ctx.sessionManager.getSessionFile() ?? "");
		opt("monitor-silence", "20");
		currentTitle = pi.getSessionName();
		setAutoNote(currentTitle);
		setState("idle");
	});
	pi.on("session_info_changed", async (event) => {
		currentTitle = event.name;
		setAutoNote(event.name);
	});

	let lastRunText = "";
	let lastRunFailed = false;
	pi.on("agent_start", async () => setState("working"));
	pi.on("ui_prompt_start", async (event) => {
		setState("asking");
		const e = event as { kind?: string; title?: string };
		const what = clean(e.title, 160) || `waiting on a ${e.kind ?? "prompt"}`;
		opt("@pi-last", clean(what, 80));
		notify("needs an answer", what);
	});
	pi.on("ui_prompt_end", async () => setState("working"));
	pi.on("agent_end", async (event) => {
		const last = event.messages?.[event.messages.length - 1] as { errorMessage?: string; stopReason?: string } | undefined;
		lastRunFailed = Boolean(last?.errorMessage || (last?.stopReason && !["stop", "end_turn", "toolUse", "tool_use"].includes(last.stopReason)));
		lastRunText = lastText(event.messages as unknown[]);
		opt("@pi-last", clean(lastRunText, 80));
		if (lastRunFailed) setState("error");
	});
	pi.on("agent_settled", async (_event, ctx) => {
		if (!ctx.isIdle()) return;
		if (lastRunFailed) notify("error", clean(lastRunText, 200) || "the run ended with an error", "critical");
		else {
			setState("done");
			notify("done", clean(lastRunText, 200) || "ready for input");
		}
	});

	pi.on("session_shutdown", async () => {
		setAutoNote(undefined);
		opt("@pi-state", "");
		opt("@pi-since", "");
		opt("@agent", "");
		opt("@pi-session", "");
		opt("@pi-last", "");
		opt("monitor-silence", "0");
	});
}
