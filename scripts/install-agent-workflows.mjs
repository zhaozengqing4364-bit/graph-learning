#!/usr/bin/env node

import { chmodSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join, relative, resolve } from "node:path";
import process from "node:process";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = resolve(SCRIPT_DIR, "..");

const TEMPLATE_SETS = {
  codex: {
    "safe-grow": resolve(ROOT_DIR, "templates/codex-safe-grow"),
    "growth-architect": resolve(ROOT_DIR, "templates/codex-growth-architect"),
  },
  claude: {
    "safe-grow": resolve(ROOT_DIR, "templates/safe-grow"),
    "growth-architect": resolve(ROOT_DIR, "templates/claude-growth-architect"),
  },
};

const COMBINED_CODEX_AGENTS_TEMPLATE = resolve(
  ROOT_DIR,
  "templates/codex-agent-kit/AGENTS.md.tpl",
);

const EXECUTABLE_BASENAMES = new Set([
  "codex-loop.sh",
  "codex-growth-plan.sh",
]);

const AGENT_CHOICES = ["codex", "claude", "both"];
const WORKFLOW_CHOICES = ["safe-grow", "growth-architect", "all"];

function printUsage() {
  console.log(`Usage: awf [target] [agent] [workflow] [options]
   or: agent-workflows [target] [agent] [workflow] [options]
   or: npm run agent:install -- --target <dir> [options]

Options:
  --target <dir>           target project directory
  --project-name <name>    template project name override
  --agent <codex|claude|both>
  --workflow <safe-grow|growth-architect|all>
  --force                  overwrite existing files
  --dry-run                print planned writes only
  --yes                    skip confirmation prompts
  --help                   show this help
`);
}

function parseArgs(argv) {
  const options = {
    agent: null,
    workflow: null,
    force: false,
    dryRun: false,
    target: null,
    projectName: null,
    yes: false,
    help: false,
  };
  const positionals = [];

  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    switch (value) {
      case "--target":
        options.target = argv[++index] ?? null;
        break;
      case "--project-name":
        options.projectName = argv[++index] ?? null;
        break;
      case "--agent":
        options.agent = argv[++index] ?? "";
        break;
      case "--workflow":
        options.workflow = argv[++index] ?? "";
        break;
      case "--force":
        options.force = true;
        break;
      case "--dry-run":
        options.dryRun = true;
        break;
      case "--yes":
      case "-y":
        options.yes = true;
        break;
      case "--help":
      case "-h":
        options.help = true;
        break;
      default:
        if (value.startsWith("-")) {
          throw new Error(`Unknown argument: ${value}`);
        }
        positionals.push(value);
    }
  }

  applyPositionals(options, positionals);
  return options;
}

function assertChoice(label, value, allowedValues) {
  if (!allowedValues.includes(value)) {
    throw new Error(`${label} must be one of: ${allowedValues.join(", ")}`);
  }
}

function renderTemplate(templatePath, projectName) {
  return readFileSync(templatePath, "utf8").replaceAll("{{PROJECT_NAME}}", projectName);
}

function normalizeAgent(value) {
  if (!value) {
    return null;
  }

  const normalized = value.toLowerCase();
  const aliases = {
    c: "codex",
    codex: "codex",
    l: "claude",
    claude: "claude",
    b: "both",
    both: "both",
  };

  return aliases[normalized] ?? null;
}

function normalizeWorkflow(value) {
  if (!value) {
    return null;
  }

  const normalized = value.toLowerCase();
  const aliases = {
    s: "safe-grow",
    safe: "safe-grow",
    "safe-grow": "safe-grow",
    g: "growth-architect",
    growth: "growth-architect",
    roadmap: "growth-architect",
    "growth-architect": "growth-architect",
    a: "all",
    all: "all",
  };

  return aliases[normalized] ?? null;
}

function applyPositionals(options, positionals) {
  for (const token of positionals) {
    if (token === "init" || token === "install" || token === "new") {
      continue;
    }

    const agent = normalizeAgent(token);
    if (agent && !options.agent) {
      options.agent = agent;
      continue;
    }

    const workflow = normalizeWorkflow(token);
    if (workflow && !options.workflow) {
      options.workflow = workflow;
      continue;
    }

    if ((token === "." || token === "here") && !options.target) {
      options.target = process.cwd();
      continue;
    }

    if (!options.target) {
      options.target = token;
      continue;
    }

    throw new Error(`Unrecognized positional argument: ${token}`);
  }
}

function listTemplateFiles(rootDir) {
  const files = [];
  const stack = [rootDir];

  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const absolutePath = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(absolutePath);
        continue;
      }
      if (entry.isFile() && extname(entry.name) === ".tpl") {
        files.push(absolutePath);
      }
    }
  }

  return files.sort();
}

function defaultedOptions(options) {
  return {
    ...options,
    agent: options.agent ?? "both",
    workflow: options.workflow ?? "all",
    target: options.target ?? process.cwd(),
  };
}

function ensureInteractiveAvailable() {
  if (!process.stdin.isTTY || !process.stdout.isTTY) {
    throw new Error("Interactive mode requires a TTY. Pass --target/--agent/--workflow explicitly.");
  }
}

function parseChoiceInput(answer, choices, defaultValue, normalizer) {
  const trimmed = answer.trim();
  if (!trimmed) {
    return defaultValue;
  }

  const numeric = Number(trimmed);
  if (Number.isInteger(numeric) && numeric >= 1 && numeric <= choices.length) {
    return choices[numeric - 1];
  }

  const normalized = normalizer(trimmed);
  if (normalized && choices.includes(normalized)) {
    return normalized;
  }

  throw new Error(`Invalid choice: ${answer}`);
}

function parseBooleanInput(answer, defaultValue) {
  const trimmed = answer.trim().toLowerCase();
  if (!trimmed) {
    return defaultValue;
  }
  if (["y", "yes", "1"].includes(trimmed)) {
    return true;
  }
  if (["n", "no", "0"].includes(trimmed)) {
    return false;
  }
  throw new Error(`Invalid yes/no answer: ${answer}`);
}

async function promptWithRetry(ask) {
  while (true) {
    try {
      return await ask();
    } catch (error) {
      console.log(error instanceof Error ? error.message : String(error));
    }
  }
}

async function runInteractivePrompts(options) {
  ensureInteractiveAvailable();

  const defaults = defaultedOptions(options);
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  try {
    console.log("Agent Workflow Installer");
    console.log("");

    const target = await promptWithRetry(async () => {
      const answer = await rl.question(`Target directory [${defaults.target}]: `);
      return resolve(answer.trim() || defaults.target);
    });

    const projectNameDefault = options.projectName ?? basename(target);
    const projectNameAnswer = await rl.question(`Project name [${projectNameDefault}]: `);
    const projectName = projectNameAnswer.trim() || projectNameDefault;

    console.log("");
    console.log("Agent target:");
    console.log("  1) codex");
    console.log("  2) claude");
    console.log("  3) both");
    const agent = await promptWithRetry(async () => {
      const answer = await rl.question(`Choose agent [3, default ${defaults.agent}]: `);
      return parseChoiceInput(answer, AGENT_CHOICES, defaults.agent, normalizeAgent);
    });

    console.log("");
    console.log("Workflow set:");
    console.log("  1) safe-grow");
    console.log("  2) growth-architect");
    console.log("  3) all");
    const workflow = await promptWithRetry(async () => {
      const answer = await rl.question(`Choose workflow [3, default ${defaults.workflow}]: `);
      return parseChoiceInput(answer, WORKFLOW_CHOICES, defaults.workflow, normalizeWorkflow);
    });

    const force = await promptWithRetry(async () => {
      const answer = await rl.question(`Overwrite existing files? [y/N, default ${options.force ? "yes" : "no"}]: `);
      return parseBooleanInput(answer, options.force);
    });

    const dryRun = await promptWithRetry(async () => {
      const answer = await rl.question(`Dry run only? [y/N, default ${options.dryRun ? "yes" : "no"}]: `);
      return parseBooleanInput(answer, options.dryRun);
    });

    console.log("");
    console.log("Summary:");
    console.log(`- target: ${target}`);
    console.log(`- project name: ${projectName}`);
    console.log(`- agent: ${agent}`);
    console.log(`- workflow: ${workflow}`);
    console.log(`- overwrite existing: ${force ? "yes" : "no"}`);
    console.log(`- dry run: ${dryRun ? "yes" : "no"}`);

    const confirmed = await promptWithRetry(async () => {
      const answer = await rl.question("Proceed? [Y/n]: ");
      return parseBooleanInput(answer, true);
    });

    if (!confirmed) {
      console.log("Cancelled.");
      process.exit(0);
    }

    return {
      ...options,
      target,
      projectName,
      agent,
      workflow,
      force,
      dryRun,
      yes: true,
    };
  } finally {
    rl.close();
  }
}

function buildSelections(agent, workflow) {
  const agents = agent === "both" ? ["codex", "claude"] : [agent];
  const workflows = workflow === "all" ? ["safe-grow", "growth-architect"] : [workflow];
  return agents.flatMap((agentName) =>
    workflows
      .filter((workflowName) => TEMPLATE_SETS[agentName][workflowName])
      .map((workflowName) => ({
        agent: agentName,
        workflow: workflowName,
        rootDir: TEMPLATE_SETS[agentName][workflowName],
      })),
  );
}

function buildPlans({ targetRoot, projectName, force, selections }) {
  const writes = new Map();
  const skipped = [];
  const selectedKeys = new Set(selections.map(({ agent, workflow }) => `${agent}:${workflow}`));
  const needsCombinedCodexAgents =
    selectedKeys.has("codex:safe-grow") && selectedKeys.has("codex:growth-architect");

  for (const selection of selections) {
    for (const templatePath of listTemplateFiles(selection.rootDir)) {
      const relativePath = relative(selection.rootDir, templatePath);
      const destination = resolve(targetRoot, relativePath.slice(0, -4));

      if (
        needsCombinedCodexAgents &&
        selection.agent === "codex" &&
        relativePath === "AGENTS.md.tpl"
      ) {
        continue;
      }

      if (existsSync(destination) && !force) {
        skipped.push(destination);
        continue;
      }

      writes.set(destination, renderTemplate(templatePath, projectName));
    }
  }

  if (needsCombinedCodexAgents) {
    const destination = resolve(targetRoot, "AGENTS.md");
    if (existsSync(destination) && !force) {
      skipped.push(destination);
    } else {
      writes.set(destination, renderTemplate(COMBINED_CODEX_AGENTS_TEMPLATE, projectName));
    }
  }

  return { writes, skipped };
}

function writePlans({ writes, skipped, dryRun }) {
  if (dryRun) {
    for (const destination of [...writes.keys()].sort()) {
      console.log(`write ${destination}`);
    }
    for (const destination of [...new Set(skipped)].sort()) {
      console.log(`skip  ${destination}`);
    }
    return;
  }

  for (const destination of [...writes.keys()].sort()) {
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, writes.get(destination), "utf8");
    if (EXECUTABLE_BASENAMES.has(basename(destination))) {
      chmodSync(destination, 0o755);
    }
    console.log(`wrote ${destination}`);
  }

  for (const destination of [...new Set(skipped)].sort()) {
    console.log(`skipped existing ${destination}`);
  }
}

function printNextSteps({ targetRoot, agent, workflow }) {
  let step = 1;

  console.log("");
  console.log("Next steps:");
  if (agent === "codex" || agent === "both") {
    console.log(
      `${step}. Fill ${resolve(targetRoot, ".codex/loop/PROJECT_GROWTH.md")} and ${resolve(
        targetRoot,
        ".codex/roadmap/PROJECT_FUTURE.md",
      )} with project-specific guidance.`,
    );
    step += 1;
    console.log(
      `${step}. Use \`scripts/codex-growth-plan.sh\` or \`scripts/codex-loop.sh\` after a dry-run preview when updating the kit.`,
    );
    step += 1;
  }
  if (agent === "claude" || agent === "both") {
    console.log(
      `${step}. Fill ${resolve(targetRoot, ".claude/loop/PROJECT_GROWTH.md")} and ${resolve(
        targetRoot,
        ".claude/roadmap/PROJECT_FUTURE.md",
      )}, then use \`/growth-architect\` or \`/safe-grow\` in Claude Code.`,
    );
    step += 1;
  }
  console.log(`${step}. Installed agent target: ${agent}; workflow set: ${workflow}.`);
}

async function main() {
  const argv = process.argv.slice(2);
  let options = parseArgs(argv);

  if (options.help) {
    printUsage();
    process.exit(0);
  }

  const missingExplicitOptions = !options.target || !options.agent || !options.workflow;
  if (missingExplicitOptions && !options.yes) {
    options = await runInteractivePrompts(options);
    runInstall(options);
    return;
  }

  options = defaultedOptions(options);
  runInstall(options);
}

function runInstall(options) {
  assertChoice("agent", options.agent, AGENT_CHOICES);
  assertChoice("workflow", options.workflow, WORKFLOW_CHOICES);

  const targetRoot = resolve(options.target);
  const projectName = options.projectName ?? basename(targetRoot);
  const selections = buildSelections(options.agent, options.workflow);
  const { writes, skipped } = buildPlans({
    targetRoot,
    projectName,
    force: options.force,
    selections,
  });

  if (options.dryRun) {
    console.log(`[dry-run] target: ${targetRoot}`);
  }

  writePlans({ writes, skipped, dryRun: options.dryRun });
  printNextSteps({
    targetRoot,
    agent: options.agent,
    workflow: options.workflow,
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  printUsage();
  process.exit(1);
});
