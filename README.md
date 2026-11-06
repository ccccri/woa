# WOA: Wake On Alexa

**"Alexa, turn on the computer"** — wake your computer with Wake on LAN from any Echo, or from
the Alexa app when you are away from home. Free and open source (MIT), forever.

WOA is an Alexa **Smart Home** skill built on Alexa's official
[`Alexa.WakeOnLANController`](https://developer.amazon.com/en-US/docs/alexa/device-apis/alexa-wakeonlancontroller.html)
interface. Your Echo, on the same network as the computer, sends the magic packet:
no Raspberry Pi, no app on the PC, no open ports.

- Website and setup page: <https://ccccri.github.io/woa/>
- Languages: English (en-US, en-GB) and Italian (it-IT)
- Only turns computers **on** (Wake on LAN cannot turn them off).

## How it works

```
 "Alexa, turn on the computer"
        │
        ▼
 Alexa cloud ── TurnOn ──▶ WOA skill Lambda ──▶ DeferredResponse
                                │ (async)
                                ├── WakeUp event ──▶ Alexa Event Gateway
                                └── Response     ──▶ Alexa Event Gateway
        │
        ▼
 Echo on the home LAN ── magic packet ──▶ computer (MAC from discovery)
```

1. **Account linking** uses Login with Amazon (`profile:user_id`). WOA only learns an anonymous user ID.
2. **Setup page** (`docs/`, GitHub Pages): the user signs in with Login with Amazon and adds
   computers (name + MAC). The API is a Lambda Function URL.
3. **Discovery** returns one endpoint per computer with `Alexa.WakeOnLANController`
   (`configuration.MACAddresses`) and `Alexa.PowerController`. New and removed computers are also
   pushed to Alexa right away with `AddOrUpdateReport` / `DeleteReport`.
4. **AcceptGrant** (`Alexa.Authorization`) gives WOA a token for the Alexa Event Gateway.
5. **TurnOn**: DeferredResponse, then `WakeUp` and the final `Response` are sent to the gateway by a
   second asynchronous invocation of the same Lambda.

The gateway must match the region of the user's Alexa account. WOA runs one backend in
`eu-west-1`, tries the EU gateway first and falls back to NA/FE when the gateway answers
`SKILL_NEVER_ENABLED_EXCEPTION`, then remembers the right region for that user.

## Repository layout

| Path | What |
| --- | --- |
| `src/woa/` | Lambda code, Python standard library only (boto3 comes with the runtime) |
| `src/woa/skill_handler.py` | Smart Home directives: Discover, AcceptGrant, TurnOn/TurnOff, ReportState |
| `src/woa/web_handler.py` | API for the setup page |
| `src/woa/gateway.py` | Alexa Event Gateway client (token refresh, region fallback, retries) |
| `tests/` | Unit tests with sample Alexa directives (`tests/events/`) |
| `template.yaml` | AWS SAM template: 2 Lambda functions + 1 DynamoDB table |
| `docs/` | GitHub Pages: home, setup page, privacy policy, terms, icons |
| `skill-package/` | Skill manifest, account linking settings, certification testing instructions |
| `tools/make_icons.py` | Regenerates the skill icons |

## Costs

Everything fits the AWS **always-free** tier for a hobby-sized skill: Lambda (1M requests/month),
DynamoDB with provisioned capacity (5 RCU/5 WCU of the free 25/25), Lambda Function URL instead of
API Gateway, CloudWatch logs kept 14 days. Login with Amazon and GitHub Pages are free.
The only paid item is the tiny S3 bucket SAM uses to upload the code (a few KB).

## Run the tests

```sh
python3 -m unittest discover -s tests -v
```

## Deploy your own copy

Prerequisites: an Amazon Developer account, an AWS account and the
[AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
(on Linux/macOS: `brew install aws-sam-cli awscli`).

1. **Login with Amazon**: create a security profile. Note its client ID and secret.
   Web Settings > Allowed Origins: your GitHub Pages origin (e.g. `https://ccccri.github.io`).
   Allowed Return URLs: the three Alexa redirect URLs shown in the skill's account linking page.
2. **Skill**: in the Alexa developer console create a *Smart Home* skill (own hosting).
   Note the skill ID.
   - *Permissions*: enable **Send Alexa Events** and note the *Alexa Skill Messaging* client ID/secret.
   - *Account linking*: Auth Code Grant, authorization URI `https://www.amazon.com/ap/oa`,
     token URI `https://api.amazon.com/auth/o2/token`, LWA client ID/secret, scope `profile:user_id`,
     authentication scheme HTTP Basic (see `skill-package/account-linking.json`).
3. **Backend**:
   ```sh
   sam deploy --guided --region eu-west-1 --stack-name woa --capabilities CAPABILITY_IAM --resolve-s3
   ```
   Answer the parameters (skill ID, LWA client ID, skill messaging client ID/secret). Later deploys:
   `sam deploy`.
4. Paste the `SkillFunctionArn` output as the skill's **Default endpoint** (and the Europe endpoint).
5. Put the `ApiUrl` output and the LWA client ID in `docs/config.js` and publish `docs/` with GitHub Pages.

## License

MIT. WOA is not affiliated with or endorsed by Amazon. Alexa and related marks are trademarks of
Amazon.com, Inc. or its affiliates.
