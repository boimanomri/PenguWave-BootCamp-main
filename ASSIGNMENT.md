# Upwind Bootcamp 2026: PenguWave Task

Take an existing security operations portal and make it significantly better.

> **Time:** ~3 hours · **Pick one track** · **AI tools encouraged** · **You present your work at the end.**

---

## Overview

You start from **PenguWave**, a frontend-only React + TypeScript starter app with mock data and an API contract. You'll pick **one** of two tracks, Backend or Frontend, and take it as far as you can in the time you have.

The task is intentionally open-ended. There is no single correct solution. You're expected to make design decisions, explain them, and build something that works end to end.

## How to approach this (the 2026 way)

Writing software in 2026 is less about typing code and more about deciding what to build and making sure it's right. Work the way you would on a real team:

- **Use AI agents freely.** Claude Code, Cursor, Codex, and similar tools are welcome.
- **You're the lead, not the typist.** You own every line. If you can't explain it, don't ship it.
- **Design before you code.** Decide what you're building and why before you prompt.
- **Review what the agent writes.** Treat it like a teammate's work. Agents are fast, confident, and sometimes confidently wrong.
- **Bring what the agent can't.** Judgment, big-picture thinking, and good taste are what make your work stand out.

We care far more about **what you understand and the decisions you made** than about how much code the agent produced.

---

## Choose your track

Pick **one** and take it as far as you can. Attempting both is a bonus, not an expectation. One track done well beats two done halfway.

| Track A: Backend | Track B: Frontend |
| --- | --- |
| Make PenguWave real, secure, and correct. | Turn the bare starter into the best security dashboard you can. |

## Starting point

The repository contains:

- A React + Vite + TypeScript frontend (a login screen, an events table, and a users page), currently running on mock data
- A set of realistic mock security events (`data/mock_events.json`)
- An API contract describing the expected endpoints (`docs/api_contract.md`)
- No backend yet; building one is Track A

Run it with `npm install` and then `npm run dev`.

> **Tip: review before you build.** Start by exploring the existing code. Part of your job is to review what's already there and fix the issues you find: bugs, security concerns, or bad patterns. Be ready to talk about what you changed and why.

---

## Track A: Backend

**Goal:** Build a real backend for PenguWave that is both correct and secure, and connect the existing frontend to it.

Your backend should:

- Implement the API described in `docs/api_contract.md` (authentication, events, users)
- Handle authentication and sessions: login, logout, and who the current user is
- Enforce authorization. Different users have different roles. Decide who is allowed to see and do what, and enforce it
- Store data in a way that survives a restart
- Validate input and return sensible, consistent errors

How you design and connect these parts is up to you. Be ready to explain the security decisions you made, and the ones you'd make with more time.

## Track B: Frontend

**Goal:** Turn the bare starter into the best security operations dashboard you can for an analyst working through the events.

Your application should make it easy to:

- See an overview of the events (for example, counts by severity, or notable hosts and tags)
- Inspect the full details of a specific event
- Narrow down results using search, filters, sorting, or any mechanism you choose
- Export the events the analyst is currently looking at (for example, CSV or JSON)
- Behave well with messy, real-world, and empty data: loading, no-results, and unusual records

Make it genuinely useful and pleasant to use. Be ready to explain your design decisions, and how your dashboard behaves when the data isn't clean.

## Technical freedom

You're free to choose your programming language, frameworks and libraries, data storage format (Track A), and application architecture.

---

## Deliverables: how to hand it in

Hand your work in the way a real team would expect, using the git workflow from the git session:

- Your code in a **Git repository**, with your work on a **branch** (not directly on `main`)
- **Small, clear commits** with messages that say what changed (e.g. `Add severity filter to events table`, not `fix` or `stuff`)
- A **Pull Request** opened when you're done, as if a teammate is going to review it
- **Merge your Pull Request into `main`** once it's ready, so `main` holds your finished work
- A short **README**: how to run your project, what you built, and the key decisions you made

> **Never commit secrets.** No `.env` files, API keys, or tokens in the repo. Use `.gitignore` to keep them out. A leaked secret is a real security incident; if you're not sure whether something is a secret, assume it is and leave it out.

## Final presentation

You'll present your work in **at most 5 minutes**, with a brief demo. We're far more interested in whether you understand and can explain what you built than in a line-by-line code walkthrough. Use the time to explain:

- Which track you chose, and **why**
- How your solution works at a high level
- One or two key decisions or challenges, and the tradeoffs you made
- Anything you found in the existing code that you changed, or would change with more time

## Evaluation

Your work will be evaluated on:

- **Your understanding and ownership of what you built** (most important)
- Whether the system works end to end
- The thoughtfulness of your design and security decisions
- Code readability and organization
- The quality of your documentation and git history: clear commits and a clean Pull Request

## Bonus (optional)

Once your chosen track is genuinely solid and you still have time, any of these can earn bonus credit:

- **Attempting both tracks**, but only if your first track is truly done. Don't start the second at the cost of the first
- Addressing the other track's concerns (for example, frontend security if you built the backend, or the reverse)
- Performance or scalability
- Handling data updates, duplicates, or bad records
- Monitoring, logging, or error handling
- Automated tests
- Any additional feature that improves the user experience or the robustness of the system
