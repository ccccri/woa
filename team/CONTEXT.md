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

Testing in development mode works only on Echo devices registered to the **same Amazon account**
as the Amazon Developer account that owns the skill.

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
- Locale → Lambda region: it-IT, en-GB → eu-west-1; en-US → us-east-1.

## Related projects of the user

- Remote access to the same PC (Tailscale, Claude Remote Control, Wake on LAN) is handled in a
  different project; WOA must not depend on it.
