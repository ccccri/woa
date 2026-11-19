# Context

Background every agent needs: who the user is, their setup, preferences and references.

## The user

- GitHub: `ccccri`. Works on a Bazzite (Fedora Atomic) desktop; uses Claude Code and OpenCode,
  alternating requests between them.
- Language: chats in **Italian**; wants everything in the repo in **English** (AGENTS.md §3).
- Owns and operates all accounts personally (Amazon Developer, AWS, Login with Amazon,
  certification). Agents give step-by-step instructions, never act on the accounts.
- Prefers: concrete step-by-step instructions, being told clearly when it is their turn,
  free solutions, open source (MIT).

## Test setup (real hardware)

| Item | Value |
| --- | --- |
| Echo | Echo Dot, same room and same network as the PC |
| PC | Bazzite desktop, wired, interface `enp9s0` (Intel I225-V, driver igc) |
| PC MAC | `c8:7f:54:0b:30:c5` (WOA format: `C8-7F-54-0B-30-C5`) |
| PC IP | 192.168.0.45, gateway 192.168.0.1 |
| Wake on LAN | Enabled in BIOS and NetworkManager (`802-3-ethernet.wake-on-lan magic`) |
| Network | Sky WiFi Hub (router) + ASUS RT-BE58U in access point mode, single LAN |
| Alexa account region | Italy → Europe (Event Gateway `api.eu.amazonalexa.com`) |

Amazon accounts (D-015): the **Echo devices are on the family Amazon account**; AWS and the Amazon
Developer account (skill owner) are on the user's **personal** account. An unpublished skill works
only for the developer account and invited **beta testers**, so the family account is invited as a
beta tester. The family account is the one that links the skill in the Alexa app, so it is also
the account to use on the WOA setup page (same LWA user_id).

## AWS account (since 2026-11-19)

| Item | Value |
| --- | --- |
| Type | **New AWS experience** ("project"), signed up with a social login; managed SCP/RCP guardrails |
| Account ID | not written here (public repo): `aws sts get-caller-identity --profile woa` |
| Project Region | **eu-north-1** (Stockholm), assigned from the contact country, cannot be changed |
| Other Regions | Denied by the `RegionFloor` SCP except us-east-1 and us-west-2 |
| Plan | FREE, USD 100 credits, expires **2027-05-19** (then Paid Plan upgrade required, irreversible) |
| CLI | AWS CLI 2.41.1 in `~/.local/bin`, profile **`woa`** via `aws login` (12 h, renews up to 90 days) |
| SAM CLI | 1.173.0, installed with `uv tool install aws-sam-cli` |
| Agent Toolkit | 25 skills in `~/.claude/skills` and `~/.agents/skills`; MCP server `aws-mcp` for Claude Code (`~/.claude.json`) and OpenCode (`~/.config/opencode/opencode.json`), env `AWS_MCP_PROXY_PROFILES=woa`; auto-update off |
| Config backup | `~/Claude/backups/agent-config-20261119-1434/` (agent configs before the toolkit) |
| MFA | Social-login projects are protected by the social provider's 2-step verification |

If an AWS command fails with expired credentials, the user runs `aws login --profile woa`.
Check the plan with `aws freetier get-account-plan-state --profile woa`.

## Amazon Developer (since 2026-11-19, personal account)

| Item | Value |
| --- | --- |
| Developer account | Personal Amazon account (already existed: old 2021 Blueprint skill "Le mie domande") |
| LWA security profile | `WOA`, privacy URL set, Allowed Origins `https://ccccri.github.io`, Return URLs not yet set |
| LWA Client ID | `amzn1.application-oa2-client.291a9a72786d49ab983dfa3165198459` (public) |
| Skill | "WOA: Wake On Alexa", Smart Home, payload v3, primary locale it-IT, Provision your own |
| Skill ID | `amzn1.ask.skill.cf0d3465-5f2e-4fb5-8b8c-c58bb27a0ab0` |
| Locales | it-IT (primary), en-US, en-GB added |
| Permissions | Send Alexa Events ON; Alexa (skill messaging) Client ID `amzn1.application-oa2-client.5212b8e810a94865a5a5c5d07e2edf60` |
| Endpoint, account linking | Being set (USER_STEPS Part 2) |

Deployment (2026-11-19): stack `woa` in eu-north-1 via `tools/deploy.sh`.
- Skill Lambda: `woa-skill` (ARN = `arn:aws:lambda:eu-north-1:<account>:function:woa-skill`)
- API (setup page): `https://ofac2ixfi2p6ug3mvkm2lofdti0hnntt.lambda-url.eu-north-1.on.aws`
- Smoke tests passed: API 401 without token, CORS allows only https://ccccri.github.io, Discover
  with a fake token returns an empty list (cold start ~4 s).
| Console | https://developer.amazon.com/alexa/console/ask (wizard: Name/Locale → Experience "Smart home", Model "Smart Home", Hosting "Provision your own" → Review) |

Note: during setup an agent's page search read part of the hidden LWA client secret; consider
"Reset Client Secret" on the LWA profile before going public (STATUS T-18).

## Glossary

- **Magic packet**: Wake on LAN frame (6×`FF` + 16× MAC) broadcast on the LAN.
- **Event Gateway**: Alexa endpoint that receives asynchronous events from skills
  (`/v3/events`), regional: EU `api.eu.amazonalexa.com`, NA `api.amazonalexa.com`,
  FE `api.fe.amazonalexa.com`.
- **AcceptGrant**: directive sent when a user links the skill; carries an auth code that WOA
  exchanges for gateway tokens.
- **LWA**: Login with Amazon (OAuth2). Used for account linking and the setup page.
- **Skill Messaging credentials**: client ID/secret under the skill's *Permissions > Send Alexa
  Events*; used for AcceptGrant token exchange and refresh.
- **Development mode**: an uncertified skill, usable only by the developer's own account/devices.

## References (verified)

- WakeOnLANController: https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-wakeonlancontroller.html
- Event Gateway: https://developer.amazon.com/en-US/docs/alexa/smarthome/send-events-to-the-alexa-event-gateway.html
- Alexa.Authorization (AcceptGrant): https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-authorization.html
- Discovery: https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-discovery.html
- Locales and Lambda regions: https://developer.amazon.com/en-US/docs/alexa/smarthome/develop-smart-home-skills-in-multiple-languages.html
- Lambda Function URL auth (SAM adds the public permissions): https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html
- Lambda Python 3.14: https://aws.amazon.com/about-aws/whats-new/2025/11/aws-lambda-python-314
- Alexa trademark guidelines: https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/trademark-guidelines

Facts collected from these pages (2026-11-06):
- TurnOn workflow: DeferredResponse (sync) → WakeUp (async, gateway) → Response/ErrorResponse.
- Gateway answers 202 on success; 401 = refresh token and retry; 403 SKILL_DISABLED = drop grant;
  403 SKILL_NEVER_ENABLED = wrong region; 429/500/503 = retry (max 3, ≥1 s apart).
- Discovery limits: 300 endpoints/user; endpointId ≤ 256 chars `[A-Za-z0-9 _\-=#;:?@&]`;
  friendlyName no punctuation; manufacturerName/description ≤ 128 chars; `COMPUTER` category exists.
- Locale → Lambda region: it-IT, en-GB → eu-west-1; en-US → us-east-1. A matching region
  "reduces latency" (implement-your-addon page); whether other regions work is tested in T-17.
- AWS new experience: project Region by contact country (us-east-2 / eu-north-1 / ap-southeast-2);
  advanced features unlock other Regions but require the irreversible Paid Plan upgrade and remove
  the spend limit (https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.md).

## Related projects of the user

- Remote access to the same PC (Tailscale, Claude Remote Control, Wake on LAN) is handled in a
  different project; WOA must not depend on it.
