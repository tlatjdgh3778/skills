#!/usr/bin/env node
/** Stamp and execute AI pipeline commits; ordinary Git commands remain unchanged. */
import { execFileSync } from "node:child_process";
import { appendFileSync, readFileSync, realpathSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$/;
const TOOL = "claude";

function sessionId(value) {
  if (typeof value !== "string" || !ID.test(value) || /^(undefined|null|unknown)$/i.test(value)) {
    throw new Error("A valid runtime session ID is required; placeholders are not accepted.");
  }
  return value;
}

export function currentSession(env = process.env) {
  const tool = env.AI_SESSION_TOOL;
  const id = env.AI_SESSION_ID;
  if (tool === undefined && id === undefined) {
    throw new Error("No runtime session ID. Commit from a Claude Code session with session tracing enabled.");
  }
  if (tool !== TOOL) throw new Error(`AI_SESSION_TOOL must be ${TOOL}.`);
  return `${tool}:${sessionId(id)}`;
}

export function startSession(payload, tool, env = process.env) {
  if (tool !== TOOL) throw new Error(`The start command requires ${TOOL}.`);
  if (payload?.hook_event_name !== "SessionStart") throw new Error("Expected a SessionStart event.");
  const id = sessionId(payload.session_id);
  if (!env.CLAUDE_ENV_FILE) throw new Error("CLAUDE_ENV_FILE is required to persist this session's environment.");
  // The allowlisted ID cannot contain shell quotes, substitutions, or newlines.
  appendFileSync(env.CLAUDE_ENV_FILE,
    `\nexport AI_SESSION_TOOL='${TOOL}'\nexport AI_SESSION_ID='${id}'\n`,
    { encoding: "utf8", mode: 0o600 });
  return {
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: `Pipeline session tracing: Session: ${tool}:${id}. For AI pipeline commits, run node ${fileURLToPath(import.meta.url)} commit <message-file>; it inserts and checks this runtime ID before committing.`,
    },
  };
}

function git(args, options = {}) {
  return execFileSync("git", ["-c", "trailer.separators=:", ...args], {
    encoding: "utf8", stdio: ["pipe", "pipe", "pipe"], ...options,
  });
}

function trailers(message, options) {
  return git(["interpret-trailers", "--parse", "--no-divider"], { ...options, input: message })
    .split("\n")
    .filter((line) => /^Session\s*:/i.test(line))
    .map((line) => {
      const value = line.replace(/^Session\s*:\s*/i, "");
      const match = /^claude:(.+)$/.exec(value);
      if (!match) throw new Error("Invalid Session trailer; expected Session: claude:<id>.");
      sessionId(match[1]);
      return value;
    });
}

export function stampCommit(filename, { env = process.env, cwd = process.cwd() } = {}) {
  const expected = currentSession(env);
  const file = resolve(cwd, filename);
  const options = { cwd, env };
  const original = readFileSync(file, "utf8");
  const content = git(["stripspace", "--strip-comments"], { ...options, input: original }).trim();
  if (!content || /^(Session|Feature|Spec|Decision)\s*:/i.test(content.split("\n")[0])) {
    throw new Error("A commit subject is required; session metadata alone is not a commit message.");
  }
  if (!trailers(original, options).includes(expected)) {
    git(["interpret-trailers", "--in-place", "--no-divider",
      "--if-exists=addIfDifferent", "--if-missing=add", "--trailer", `Session: ${expected}`, file], options);
  }
  if (!trailers(readFileSync(file, "utf8"), options).includes(expected)) {
    throw new Error("The final commit message is missing its runtime Session trailer.");
  }
  return expected;
}

export function commitWithSession(filename, { env = process.env, cwd = process.cwd() } = {}) {
  const options = { env, cwd };
  const expected = stampCommit(filename, options);
  const output = git(["commit", "-F", resolve(cwd, filename)], options);
  const hash = git(["rev-parse", "HEAD"], options).trim();
  const committedMessage = git(["log", "-1", "--format=%B"], options);
  if (!trailers(committedMessage, options).includes(expected)) {
    throw new Error(`Commit ${hash} was created but its Session trailer changed. Inspect the existing Git hooks; no automatic amend was performed.`);
  }
  return output;
}

function main() {
  const [mode, argument, ...extra] = process.argv.slice(2);
  if (!argument || extra.length) throw new Error("Usage: session-stamp.mjs start claude | commit <message-file>");
  if (mode === "start") {
    process.stdout.write(`${JSON.stringify(startSession(JSON.parse(readFileSync(0, "utf8")), argument))}\n`);
  } else if (mode === "commit") {
    process.stdout.write(commitWithSession(argument));
  } else {
    throw new Error(`Unknown mode: ${mode}`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  try {
    main();
  } catch (error) {
    console.error(`[session-stamp] ${error.message}`);
    process.exitCode = 1;
  }
}
