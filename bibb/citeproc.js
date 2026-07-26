#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const CSL = require("citeproc");

function parseInput(raw) {
  const payload = JSON.parse(raw);

  if (!payload.style || !payload.locale || !Array.isArray(payload.items)) {
    throw new Error("Invalid output.json format: expected style, locale, and items fields.");
  }

  return payload;
}

function loadInput(inputArg) {
  if (inputArg === "-") {
    return parseInput(fs.readFileSync(0, "utf8"));
  }

  return parseInput(fs.readFileSync(inputArg, "utf8"));
}

function normalizeItems(items) {
  const byId = {};

  for (const entry of items) {
    if (!entry || typeof entry !== "object") {
      continue;
    }

    // The input stores each item as { "<doi>": { ...csl item... } }.
    for (const value of Object.values(entry)) {
      if (!value || typeof value !== "object") {
        continue;
      }

      const item = { ...value };
      if (!item.id) {
        throw new Error("Encountered an item without an id.");
      }
      byId[item.id] = item;
    }
  }

  const ids = Object.keys(byId);
  if (ids.length === 0) {
    throw new Error("No CSL items found in output.json.");
  }

  return { byId, ids };
}

function preprocessStyle(styleXml) {
  const titleMacroPattern = /<macro\s+name="title">[\s\S]*?<\/macro>/;
  const normalizedTitleMacro = "<macro name=\"title\"><text variable=\"title\"/></macro>";

  if (!titleMacroPattern.test(styleXml)) {
    return styleXml;
  }

  return styleXml.replace(titleMacroPattern, normalizedTitleMacro);
}

function buildProcessor(styleXml, localeXml, itemsById) {
  const sys = {
    retrieveLocale: () => localeXml,
    retrieveItem: (id) => itemsById[id],
  };

  return new CSL.Engine(sys, styleXml);
}

function formatBibliography(engine, ids) {
  engine.setOutputFormat("text");
  engine.updateItems(ids);
  const bibResult = engine.makeBibliography();

  if (!bibResult || !Array.isArray(bibResult) || !Array.isArray(bibResult[1])) {
    throw new Error("Unexpected bibliography output from citeproc-js.");
  }

  return bibResult[1].join("\n");
}

function main() {
  const jsonPath = path.resolve(process.argv[2] || "output.json");
  const inputArg = process.argv[2] === "-" ? "-" : jsonPath;
  const payload = loadInput(inputArg);
  const { byId, ids } = normalizeItems(payload.items);
  const preprocessedStyle = preprocessStyle(payload.style);

  const engine = buildProcessor(preprocessedStyle, payload.locale, byId);
  const rendered = formatBibliography(engine, ids);

  process.stdout.write(`${rendered}\n`);
}

try {
  main();
} catch (error) {
  console.error(`Error: ${error.message}`);
  process.exit(1);
}
