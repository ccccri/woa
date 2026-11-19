# Decisions

Settled decisions with their reasons. Do not silently undo one: add a new entry that
supersedes it (and mark the old one "Superseded by D-xxx"). Newest at the bottom.

Format: `## D-NNN — Title` · date · who · Decision · Why · Consequences/sources.

---

## D-001 — Smart Home skill with Alexa.WakeOnLANController
2026-11-06 · user + claude
**Decision:** Use the official `Alexa.WakeOnLANController` + `Alexa.PowerController` interfaces.
**Why:** The Echo on the same LAN sends the magic packet, so users need no extra hardware,
no app on the PC and no open ports. That is what made wolskill.com work.
**Source:** https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-wakeonlancontroller.html

## D-002 — AWS Lambda (Python) + DynamoDB in eu-west-1, deployed with SAM
2026-11-06 · user
**Decision:** One SAM stack (`woa`) in `eu-west-1`; Python stdlib only.
**Why:** Free tier, user's region (Italy → Europe Alexa region), one-command deploy.

## D-003 — Stay inside the AWS always-free tier
2026-11-06 · user + claude
**Decision:** Lambda Function URL instead of API Gateway (API Gateway is free only for 12 months);
DynamoDB PROVISIONED 5/5 (free 25/25) instead of on-demand; no Secrets Manager (paid): the two
skill-messaging credentials are NoEcho CloudFormation parameters stored as Lambda environment
variables (encrypted at rest); CloudWatch log retention 14 days.
**Consequences:** the only non-free item is the tiny SAM upload bucket (`--resolve-s3`, a few KB).

## D-004 — TurnOn uses DeferredResponse + async self-invocation
2026-11-06 · claude
**Decision:** The skill Lambda answers TurnOn with a synchronous `DeferredResponse`, then invokes
itself asynchronously (`{"task": "woa.wake"}`) to send `WakeUp` and the final `Response`
(or `ErrorResponse`) to the Alexa Event Gateway. If the async invoke fails, it falls back to
sending WakeUp inline and answering with a synchronous `Response`.
**Why:** It is the exact workflow in Amazon's WakeOnLANController docs.

## D-005 — MAC format in discovery: uppercase with dashes
2026-11-06 · claude
**Decision:** Normalize any input format to `AA-BB-CC-DD-EE-FF`. Reject multicast, all-zero and
broadcast addresses.
**Why:** The Amazon docs example uses dashes. (Unverified on real traffic; see STATUS.)

## D-006 — Single backend, Event Gateway region fallback
2026-11-06 · claude
**Decision:** Try the EU gateway first, then NA, then FE, moving on when the gateway answers
`403 SKILL_NEVER_ENABLED_EXCEPTION`; store the working region per user in the GRANT item.
Order configurable with the `GatewayOrder` SAM parameter.
**Why:** en-US belongs to the North America region officially, but one backend is simpler and free.
A wrong region answers 403 SKILL_NEVER_ENABLED (per the event gateway docs).
**Source:** https://developer.amazon.com/en-US/docs/alexa/smarthome/send-events-to-the-alexa-event-gateway.html

## D-007 — Identify users with LWA tokeninfo + audience check
2026-11-06 · claude
**Decision:** Every token (Alexa directives and the setup page) is resolved with
`https://api.amazon.com/auth/o2/tokeninfo`; the `aud` must equal our LWA client ID. Results are
cached in DynamoDB by SHA-256 of the token until expiry (TTL).
**Why:** Rejects tokens issued to other apps; one HTTP call; no profile data needed.

## D-008 — Power state not retrievable
2026-11-06 · claude
**Decision:** `powerState` is declared with `retrievable: false`, `proactivelyReported: false`.
ReportState returns only `EndpointHealth.connectivity = OK`. TurnOff returns
`NOT_SUPPORTED_IN_CURRENT_MODE` (currentDeviceMode OTHER).
**Why:** WOA cannot know whether a PC is on; reporting a fake state would mislead users.

## D-009 — Push discovery changes from the setup page
2026-11-06 · claude
**Decision:** Adding/removing a computer sends `AddOrUpdateReport` / `DeleteReport` (best effort);
if it fails the page tells the user to say "Alexa, discover devices".
**Why:** Better UX; no extra cost.

## D-010 — Limits
2026-11-06 · claude
**Decision:** Max 20 computers per user; friendly name 1-64 chars, letters/digits/spaces only
(Alexa forbids punctuation); request body ≤ 2 KB.

## D-011 — Skill name "WOA: Wake On Alexa" (at risk)
2026-11-06 · user (name) / claude (risk)
**Decision:** Keep the user's chosen name for development. Fallback if certification objects:
"WOA - Wake on LAN".
**Why:** Amazon trademark guidelines discourage combining a third-party name with "Alexa".
**Source:** https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/trademark-guidelines

## D-012 — Team workflow: Claude Code and OpenCode alternate
2026-11-19 · user + claude
**Decision:** Shared memory lives in the repo (`AGENTS.md`, `team/`). Each turn starts with
`tools/handoff.py start` and ends with a `team/LOG.md` entry, `STATUS.md` update and
`tools/handoff.py end`. Agents commit locally each turn; push only when the user asks.
**Why:** The user alternates requests between Claude Code and OpenCode; neither can read the
other's private memory or chat.
