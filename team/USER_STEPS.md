# Steps the user does personally

Account and agreement steps are **always done by the user** (AGENTS.md §6). Agents explain them
in Italian in chat, using this file as the source. Mark progress in `team/STATUS.md`.

Use the **same Amazon account as your Echo devices** everywhere: development-mode skills only
work on the developer account's own devices.

---

## Part 1 — Accounts, security profile, skill, deploy (STATUS T-09)

### 1.1 AWS account
1. Sign up at https://aws.amazon.com (needs a card).
2. Enable MFA on the root user: account menu → *Security credentials*.
3. Billing → *Budgets* → *Create budget* → **Zero spend budget**, with your email. It warns you
   if anything costs even one cent.
4. IAM → *Users* → *Create user* `woa-deployer`, attach policy `AdministratorAccess`.
   Open the user → *Security credentials* → *Create access key* → *Command Line Interface*.
5. In a terminal: `brew install aws-sam-cli awscli`, then `aws configure`
   (paste the two keys, region `eu-west-1`, output `json`).

### 1.2 Amazon Developer account
Sign up at https://developer.amazon.com (free) and complete the profile (payment info is not
needed for a free skill).

### 1.3 Login with Amazon security profile
1. https://developer.amazon.com/loginwithamazon/console/site/lwa/overview.html →
   *Create a New Security Profile*: name `WOA`, description `WOA - Wake On Alexa`,
   privacy notice URL `https://ccccri.github.io/woa/privacy.html`.
2. Open the profile → *Web Settings* → *Edit* → **Allowed Origins**: `https://ccccri.github.io`.
   (Allowed Return URLs are added in Part 2.)
3. Note the **Client ID** (not secret) and keep the **Client Secret** private.

### 1.4 Create the skill
1. https://developer.amazon.com/alexa/console/ask → *Create Skill*:
   name `WOA: Wake On Alexa`, primary locale **Italian (IT)**, type **Smart Home**,
   hosting **Provision your own**.
2. Note the **Skill ID** (`amzn1.ask.skill.…`).
3. Language menu (top left) → add **English (US)** and **English (UK)**.
4. Left menu **Permissions** → enable **Send Alexa Events** → note the
   **Alexa Skill Messaging Client ID** and keep the **Client Secret** private.

### 1.5 Deploy the backend
In your own terminal (so the secret never goes through an agent):
```sh
cd ~/Claude/woa
sam deploy --guided --region eu-west-1 --stack-name woa --capabilities CAPABILITY_IAM --resolve-s3
```
Answers: `SkillId`, `LwaClientId` (1.3), `AlexaClientId` and `AlexaClientSecret` (1.4); defaults
for everything else; "Save arguments to configuration file" = yes (`samconfig.toml` is git-ignored).

**Give the agent:** the outputs `SkillFunctionArn` and `ApiUrl`, and the LWA **Client ID**.
Never paste secrets in chat.

---

## Part 2 — Connect skill and backend (STATUS T-11, after the agent did T-10)

1. Skill → *Smart Home* → **Default endpoint**: paste `SkillFunctionArn`; tick **Europe, India**
   and paste the same ARN; also tick **North America** with the same ARN (en-US). Save.
2. Skill → **Account Linking**:
   - Authorization grant type: *Auth Code Grant*
   - Web Authorization URI: `https://www.amazon.com/ap/oa`
   - Access Token URI: `https://api.amazon.com/auth/o2/token`
   - Client ID / Client Secret: from the LWA security profile (1.3)
   - Client Authentication Scheme: *HTTP Basic*
   - Scope: `profile:user_id`
   - Save, then copy the three **Alexa Redirect URLs** shown on the page.
3. LWA security profile → *Web Settings* → *Edit* → **Allowed Return URLs**: paste the three
   redirect URLs. Save.
4. Skill → *Distribution* → fill the listing per locale (texts are in `skill-package/skill.json`),
   icons `https://ccccri.github.io/woa/assets/icon-108.png` and `icon-512.png`, privacy
   `https://ccccri.github.io/woa/privacy.html`, terms `https://ccccri.github.io/woa/terms.html`.
5. Skill → *Test* tab → set testing to **Development**.

## Part 3 — First real test (STATUS T-14)

1. Alexa app → *More* → *Skills & Games* → *Your Skills* → *Dev* → **WOA** → *Enable* → log in.
2. Open https://ccccri.github.io/woa/setup.html → sign in with Amazon → add the PC
   (`PC` or `computer`, MAC `c8:7f:54:0b:30:c5`).
3. Shut the PC down (normal shutdown, cable connected).
4. Say "Alexa, accendi computer" to the Echo Dot. Also try from the Alexa app away from Wi-Fi.
5. Report to the agent what Alexa said and whether the PC woke up. The agent may ask you to open
   CloudWatch logs: AWS console → CloudWatch → Log groups → `/aws/lambda/woa-skill`.

## Part 4 — Certification (STATUS T-15)

1. Skill → *Certification* → *Validation* → run and fix what it reports (agent helps).
2. *Submission* → submit for certification. Testing instructions are in
   `skill-package/TESTING_INSTRUCTIONS.txt`.
3. Answer certification feedback with an agent; resubmit if needed.
