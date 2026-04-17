---
name: avoid over-engineering
description: User pushed back on complex solutions; prefers the simplest working approach
type: feedback
---

Prefer the simplest working approach, don't start with the most powerful tool.

**Why:** When presented with Playwright + network interception, user asked "is it effective enough?" and later called mitmproxy "very complex". Ended up using plain `requests` after discovering the API from the page source — zero browser needed.

**How to apply:** For scraping/automation tasks, try inspecting page source for API endpoints before reaching for headless browsers or proxy interception tools. Only escalate complexity if the simple path is exhausted.
