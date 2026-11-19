# Architecture

Technical reference for WOA. Keep it in sync with the code (AGENTS.md §6).

## 1. Components

```
                ┌──────────────── AWS eu-west-1 (stack "woa") ────────────────┐
 Alexa cloud ──▶│ woa-skill  (Lambda, AlexaSkill trigger restricted to SkillId)│
                │   ▲  async self-invoke {"task":"woa.wake"}                   │
                │   └──┘                                                       │
 Setup page ───▶│ woa-web    (Lambda Function URL, CORS = GitHub Pages origin) │
 (GitHub Pages) │                                                              │
                │ woa-data   (DynamoDB, provisioned 5/5, TTL on "ttl")         │
                └──────────────────────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
 api.amazon.com (LWA)      Alexa Event Gateway (EU / NA / FE)
 tokeninfo, token                         │
                                          ▼
                             Echo on the user's LAN ── magic packet ──▶ PC
```

## 2. Code map (`src/woa/`)

| Module | Responsibility |
| --- | --- |
| `skill_handler.py` | Entry point of `woa-skill`. Routes directives; runs the async wake task. |
| `web_handler.py` | Entry point of `woa-web`. REST API for the setup page. |
| `alexa.py` | All Alexa message builders (responses and gateway events). |
| `gateway.py` | Event Gateway client: token refresh, region fallback, retries. |
| `lwa.py` | `UserResolver` (token → user_id via tokeninfo, cached) and `GrantClient` (code exchange/refresh). |
| `store.py` | `DynamoStore` (real) and `MemoryStore` (same API, tests). |
| `services.py` | Builds `Services` from environment variables; tests build it with fakes. |
| `validation.py` | MAC and friendly-name validation/normalization. |
| `net.py` | Minimal urllib HTTP client returning `Response(status, json_body)`. |

Every handler accepts `svc=` so tests can inject `tests/fakes.make_services()`.

## 3. Flows

### 3.1 Account linking + AcceptGrant
1. User enables the skill in the Alexa app → LWA login (scope `profile:user_id`).
2. Alexa sends `Alexa.Authorization.AcceptGrant` with `grant.code` and `grantee.token`.
3. `accept_grant`: `grantee.token` → user_id (tokeninfo); `grant.code` → tokens via
   `POST https://api.amazon.com/auth/o2/token` with the **Skill Messaging** client credentials.
4. Store GRANT item (keeps the previously learned region). Reply `AcceptGrant.Response`,
   or `ErrorResponse` type `ACCEPT_GRANT_FAILED`.

### 3.2 Setup page
1. `docs/setup.html` loads the LWA JS SDK, `amazon.Login.authorize({scope:"profile:user_id",
   response_type:"token", popup:true})`. Token kept in `sessionStorage` only.
2. Calls the API with `Authorization: Bearer <token>`.

| Method + path | Body | Result |
| --- | --- | --- |
| `GET /api/me` | – | `{devices:[{id,name,mac}], linked:bool, maxDevices}` |
| `POST /api/devices` | `{name, mac}` | 201 `{device, synced}`; 400 invalid; 409 duplicate/limit |
| `DELETE /api/devices/<id>` | – | `{deleted:true, synced}`; 404 |
| `DELETE /api/me` | – | `{deleted:true}` (all user data) |

`linked` = a GRANT exists. `synced` = AddOrUpdateReport/DeleteReport accepted by the gateway.

### 3.3 Discovery
`Alexa.Discovery.Discover` → `payload.scope.token` → user_id → one endpoint per device:
`endpointId` = `woa-<16 hex>`, `displayCategories ["COMPUTER"]`, capabilities `Alexa`,
`Alexa.WakeOnLANController` (`configuration.MACAddresses: ["AA-BB-..."]`),
`Alexa.PowerController` (powerState not retrievable), `Alexa.EndpointHealth` (connectivity).
Invalid token → empty endpoint list (logged).

### 3.4 TurnOn
1. Token → user_id; endpoint must belong to the user (else `NO_SUCH_ENDPOINT`); invalid token →
   `INVALID_AUTHORIZATION_CREDENTIAL`; no GRANT → `INTERNAL_ERROR` asking to re-enable the skill.
2. `invoke_async({"task":"woa.wake", user_id, endpoint_id, correlation_token})` and return
   `Alexa.DeferredResponse` (`estimatedDeferralInSeconds: 5`).
3. Async invocation `run_wake`: gateway `WakeUp` event (context powerState OFF), then gateway
   `Alexa.Response` (powerState ON) or `ErrorResponse ENDPOINT_UNREACHABLE`.
4. Fallback if the async invoke raises/returns false: send WakeUp inline, return sync `Response`.

### 3.5 Other directives
- TurnOff → `ErrorResponse NOT_SUPPORTED_IN_CURRENT_MODE` (`currentDeviceMode: OTHER`).
- ReportState → `StateReport` with `EndpointHealth.connectivity OK` only.
- Anything else → `ErrorResponse INVALID_DIRECTIVE`.

## 4. Event Gateway client (`gateway.py`)

`Gateway.send(user_id, build)` where `build(access_token)` returns the event body:
1. Load GRANT; refresh if expiring within 120 s. Refresh failure → delete GRANT, raise `NoGrant`.
2. Regions to try: stored region first, then `GATEWAY_ORDER` (default `EU,NA,FE`).
3. POST with retries on 0/429/500/503 (max 3 attempts, 1 s apart).
4. 401 → force refresh once and retry. 403 `SKILL_NEVER_ENABLED_EXCEPTION` → next region.
   403 `SKILL_DISABLED_EXCEPTION` → delete GRANT, raise `NoGrant`. 202/200 → save region, True.
   Anything else → False.

## 5. Data model (DynamoDB table `woa-data`)

| pk | sk | Attributes |
| --- | --- | --- |
| `USER#<user_id>` | `DEVICE#<endpoint_id>` | `name`, `mac`, `created_at` |
| `USER#<user_id>` | `GRANT` | `access_token`, `refresh_token`, `expires_at`, `region` |
| `TOKEN#<sha256(token)>` | `USER` | `user_id`, `expires_at`, `ttl` (expires_at + 1 h) |

The table has `DeletionPolicy: Retain` so deleting the stack keeps user data.

## 6. Configuration

SAM parameters → environment variables:

| Parameter | Env var | Secret? | Where it comes from |
| --- | --- | --- | --- |
| `SkillId` | (trigger only) | no | Alexa console |
| `LwaClientId` | `LWA_CLIENT_ID` | no | LWA security profile |
| `AlexaClientId` | `ALEXA_CLIENT_ID` | no | Skill > Permissions > Send Alexa Events |
| `AlexaClientSecret` | `ALEXA_CLIENT_SECRET` | **yes** (NoEcho) | same |
| `SetupPageOrigin` | (CORS) | no | default `https://ccccri.github.io` |
| `GatewayOrder` | `GATEWAY_ORDER` | no | default `EU,NA,FE` |

Front end: `docs/config.js` holds `lwaClientId` and `apiUrl` (both public). While they contain
`REPLACE_ME` the setup page shows "not configured".

Stack outputs: `SkillFunctionArn` (skill endpoint), `ApiUrl` (setup page API).

## 7. Security notes

- Skill Lambda can be invoked only by the Alexa skill (`AlexaSkill` event with `SkillId`) and by
  itself (IAM policy limited to its own ARN). The `task` path is therefore not reachable from outside.
- Web Lambda is public (Function URL, AuthType NONE) but every route requires a valid LWA token
  for our client ID; users only ever see their own `USER#` partition.
- No tokens, MACs or user IDs in logs.
- Front end builds DOM with `textContent`; token in `sessionStorage` only.

## 8. Tests

- `tests/test_skill.py`: directives with `tests/events/*.json`; gateway sequences, region
  fallback, 401 refresh, disabled skill, sync fallback.
- `tests/test_web.py`: API routes, validation, limits, user isolation.
- `tests/test_store_dynamo.py`: `DynamoStore` with moto (skipped if moto missing).
- `tests/fakes.py`: `FakeHttp` (answers tokeninfo/token; gateway answers queued per URL with
  `queue(url, Response...)`, default 202), `make_services()`.
