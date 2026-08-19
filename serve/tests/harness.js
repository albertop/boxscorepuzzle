/**
 * A test runner small enough to read in one sitting, because there is no Node on this machine and the
 * engine is meant to run with a JSON file and nothing else.
 *
 * ⚠️ **The failure output names the case and the values, never just "failed".** A red dot that does not
 * say what it expected sends you back to the source to guess, which is how a green suite and a broken
 * guard become indistinguishable.
 */

const suites = [];
let current = null;

export function suite(name, body) {
  current = { name, cases: [] };
  suites.push(current);
  body();
  current = null;
}

export function test(name, body) {
  current.cases.push({ name, body });
}

export function assert(condition, message) {
  if (!condition) throw new Error(message ?? "assertion failed");
}

export function equal(actual, expected, message) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) throw new Error(`${message ?? "not equal"}: got ${a}, expected ${b}`);
}

export function throws(body, pattern, message) {
  try {
    body();
  } catch (error) {
    if (pattern && !new RegExp(pattern).test(String(error.message))) {
      throw new Error(`${message ?? "wrong error"}: ${error.message} does not match ${pattern}`);
    }
    return error;
  }
  throw new Error(message ?? `expected a throw matching ${pattern}`);
}

export async function run(into) {
  let passed = 0;
  const failures = [];
  for (const group of suites) {
    const section = document.createElement("section");
    section.innerHTML = `<h2></h2>`;
    section.querySelector("h2").textContent = group.name;
    for (const item of group.cases) {
      const line = document.createElement("p");
      try {
        await item.body();
        line.className = "pass";
        line.textContent = `✓ ${item.name}`;
        passed += 1;
      } catch (error) {
        line.className = "fail";
        line.textContent = `✗ ${item.name} — ${error.message}`;
        failures.push(`${group.name} / ${item.name}: ${error.message}`);
      }
      section.append(line);
    }
    into.append(section);
  }
  const summary = document.createElement("h1");
  summary.className = failures.length ? "fail" : "pass";
  summary.textContent = failures.length ? `${failures.length} FAILED, ${passed} passed` : `${passed} passed`;
  into.prepend(summary);
  // Read by the harness driver rather than scraped from the page text.
  globalThis.__results = { passed, failures };
  document.title = summary.textContent;
}
