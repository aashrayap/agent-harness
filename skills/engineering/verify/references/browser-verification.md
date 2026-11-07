# Browser-Driven Verification

For verifying GUI/web changes by driving a real browser, especially behind
enterprise SSO. Load this when the surface is a web app.

## Signed-in browser first, Playwright as fallback

Drive the already signed-in browser through the runtime's browser tool when
one is available (Claude Code: Claude in Chrome; Codex: Computer Use). Fall
back to a Playwright persistent profile only when it is not, preferring the
project's bundled Playwright (`node_modules/playwright`).

## Persistent profile: log in once

Use a persistent context pointed at a fixed profile dir so SSO cookies survive
across runs; only the first run needs a manual login. Run headed: SSO and MFA
often block headless browsers.

```js
import { chromium } from '<project>/node_modules/playwright/index.mjs'

export async function launch() {
  const ctx = await chromium.launchPersistentContext('/tmp/<app>-verify/profile', {
    headless: false,
    viewport: { width: 1600, height: 1000 },
  })
  const page = ctx.pages()[0] ?? (await ctx.newPage())
  return { ctx, page }
}
```

## Multi-hop enterprise auth: wait for the APP origin

Enterprise login is not one redirect. A typical chain is
`login.microsoftonline.com` → an account picker → a federation IdP
(`federation.<corp>.com` / PingFed) → back to the app origin. The classic bug:
treat "URL no longer contains `login.microsoftonline.com`" as "authed". The
script then races ahead onto the IdP hop and dumps an unloaded page.

Wait for the **app origin** specifically, and auto-click the account-picker
tile along the way. `APP_ORIGIN` is the app's own origin, such as the local
dev server; the loop polls because the IdP hop is slow.

```js
const APP_ORIGIN = '<app-origin>'

export async function gotoAuthed(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' })
  const deadline = Date.now() + 300000
  while (Date.now() < deadline && !page.url().startsWith(APP_ORIGIN)) {
    if (page.url().includes('login.microsoftonline.com')) {
      const tile = page.locator('.row.tile, [data-test-id*="<name>"]', { hasText: /<name>/i }).first()
      if (await tile.count().catch(() => 0)) await tile.click().catch(() => {})
    }
    await page.waitForTimeout(1500)
  }
  if (!page.url().startsWith(APP_ORIGIN)) throw new Error(`AUTH_FAILED at ${page.url()}`)
}
```

After landing, also wait for real content (e.g. grid rows), not just
`domcontentloaded` — data loads after the SPA mounts. If a wait times out,
screenshot before reloading once; the screenshot usually shows the actual
state (an account picker, an error toast, an empty filter).

## Assert behavior from the network, not just pixels

Attach request/response listeners to capture exact payload shape and status —
this is how you prove a contract (camelCase fields, renamed keys, conditional
fields sent only when changed).

```js
page.on('request', r => {
  if (r.method() === 'PUT' && r.url().includes('<endpoint>'))
    console.log('>>PUT', r.url(), 'BODY:', r.postData())
})
page.on('response', r => {
  if (r.request().method() === 'PUT' && r.url().includes('<endpoint>'))
    console.log('<<PUT', r.status())
})
```

## Probe mutations without writing to shared dev data

To verify *what a Save would send* without persisting it to a shared dev
database, intercept and abort the request. You capture the payload; the server
never sees it.

```js
await page.route('**/<endpoint>', route => {
  if (route.request().method() === 'PUT') {
    console.log('ABORTED_PUT_BODY:', route.request().postData())
    return route.abort()
  }
  return route.continue()
})
```

Then trigger Save, call `page.unroute('**/<endpoint>')` and cancel out.

## When you do mutate, revert it

If a check requires a real write (the create/commit path itself is under test),
undo it in the same run: edit-then-revert (save new value, then save the
original back), or add-then-remove (add the link/attachment, then delete it).
Confirm the revert with its own assertion (element count back to 0, value back
to original) so no test rows pollute the shared dev database.

## Evidence

Screenshot each meaningful state to a stable dir
(`/tmp/<app>-verify/evidence/NN-step.png`) and Read them back as your visual
evidence. Pair each screenshot with the captured network line so the reader
sees both the pixels and the payload.

## Run-loop shape

Keep a shared `lib.mjs` (`launch`, `gotoAuthed`, `dumpGridRows`) and one small
script per phase that imports it. Phases are cheap to rerun because the profile
persists the login. Run scripts in the background and poll their output file
for a completion marker rather than blocking.

## Selector gotchas

- Form field order is not obvious — a section labeled "Links" may put URL
  first and display-text second. Read the rendered labels (or screenshot)
  before deciding which input is which. Filling them backwards makes a valid
  form look broken (e.g. a URL field rejecting a non-URL → Add stays disabled),
  which reads as a false FAIL.
- React-controlled inputs need real events: prefer `.click()` then
  `keyboard.type(...)` over `.fill(...)` when a value doesn't "take" / a button
  stays disabled.
- Custom dropdowns (Chakra/Radix) are not `<select>` — click the trigger by its
  current text, then click the option from the listbox.
