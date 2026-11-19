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
**Region part superseded by D-013.**
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

## D-013 — Deploy region: eu-north-1 (Stockholm) instead of eu-west-1 (to verify)
2026-11-19 · claude (proposed, pending the T-17 test)
**Decision:** Deploy the stack in the user's AWS project Region **eu-north-1**. The code and
template are region-independent; only the `--region` flag and docs change.
**Why:** The user's AWS account is a "new AWS experience" project. Projects are assigned one
Region by contact country (Europe → eu-north-1) and a managed SCP (`RegionFloor`) denies other
Regions except us-east-1 and us-west-2. eu-west-1 is reachable only by upgrading to the Paid Plan
and activating advanced features, both irreversible (and it removes the spend limit).
Alexa docs map the Europe endpoint to Ireland but say a matching region only "reduces latency",
so a Stockholm Lambda should work; to be confirmed in T-17.
**Fallbacks, in order:** us-east-1 (allowed by the SCP; canonical North America region),
then advanced features + eu-west-1 (user's decision only).
**Sources:** https://docs.aws.amazon.com/accounts/latest/reference/project-regions.md ·
https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html ·
https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.md ·
https://developer.amazon.com/en-US/docs/alexaplus/smarthome/implement-your-addon.html

## D-014 — AWS access via `aws login` and the AWS Agent Toolkit
2026-11-19 · user
**Decision:** The AWS CLI uses profile `woa`, authenticated with `aws login` (browser, 12 h
credentials renewable for 90 days; no access keys). The AWS Agent Toolkit is installed for both
Claude Code and OpenCode (25 AWS skills, `aws-mcp` MCP server pointed at profile `woa`), with
automatic skill updates **off**. AWS rules from the toolkit are **not** added to this repo.
**Why:** The user chose it; `aws login` avoids long-lived IAM keys (supersedes the IAM user +
access key steps first written in USER_STEPS 1.1).
**Consequences:** Agents can act on the user's AWS project. Agents still ask before creating,
changing or deleting AWS resources, and never enter secrets on the user's behalf.

## D-015 — Developer account personal, family account as beta tester
2026-11-19 · user
**Decision:** The Amazon Developer account (skill owner and public author) is the user's personal
Amazon account, like AWS. The Echo devices are on the family Amazon account, which is invited as a
**beta tester** to use WOA before publication.
**Why:** Keeps the skill under the user's own name; unpublished skills only work for the developer
account and beta testers.
**Consequences:** Account linking and the setup page are used with the family account.
