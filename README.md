# Unraid Community Applications starter

Template repository for new app repos under [unraid-apps](https://github.com/unraid-apps). Click **Use this template** on GitHub, name the new repo after the app (lowercase, e.g. `freellmapi`), then work through the checklist below. First real instance: [unraid-apps/freellmapi](https://github.com/unraid-apps/freellmapi).

## What is in here

```
ca_profile.xml                     repository profile shown in CA (root, required)
templates/APPNAME.xml.example      documented Docker template skeleton, incl. Tailscale fields
scripts/validate-template.py       XML checks: structure, Config attributes, reachable Icon/TemplateURL
.github/workflows/validate.yml     runs the validator on push and PR
.github/ISSUE_TEMPLATE/            "template problem here, app problem upstream" routing
.github/dependabot.yml             keeps the GitHub Actions current
optional/wrapper-image/            only if the upstream image needs help to run on Unraid (see below)
LICENSE                            MIT
```

## Checklist for a new app

1. **Template.** Copy `templates/APPNAME.xml.example` to `templates/<appname>.xml`. Replace every `APPNAME` and `TODO`, delete the comments you do not need. Rules of thumb: fields the average user must touch get `Display="always"`, everything else `Display="advanced"`; secrets get `Mask="true"`; only expose variables that cannot be set in the app's own UI.
2. **Icon.** Put a square PNG (256–512 px) in the repo root as `<appname>-icon.png` and point `<Icon>` at its raw URL on `main`. Copying the upstream icon is fine under a permissive license; credit it in the README.
3. **Profile.** Fill `<Profile>` in `ca_profile.xml`. Optional `<Forum>` once an Unraid forum thread exists.
4. **README.** Install steps, first-start notes, template fields, backup, support split (template here, app upstream), credits and license.
5. **Issue templates.** Replace the upstream link in `.github/ISSUE_TEMPLATE/config.yml` and the placeholder in `unraid-template.yml`.
6. **Validate locally:** `python3 scripts/validate-template.py --check-urls ca_profile.xml templates/*.xml` (URLs resolve only after the first push).
7. **Push to `main`.** `<TemplateURL>` must point at the raw file on `main`; CA refreshes templates from it.
8. **Test on a real Unraid.** Settings → Docker → Advanced View → Template repositories → add the repo URL → Docker → Add Container → pick the template. Install, start, open the WebUI, remove, reinstall with existing appdata.
9. **Submit.** Go to [ca.unraid.net/submit](https://ca.unraid.net/submit), enter the repository URL, run **Validate**, then **Scan**. Fix whatever it reports and repeat after every meaningful XML change. Requirements as of 2026: public and active repo, OSI license, `ca_profile.xml` with non-empty `<Profile>`, one XML per app, `<Repository>` pointing at an existing image, 2FA on the GitHub account.
10. **Maintain.** Keep the template working on new Unraid releases, answer issues, and tell the CA moderators if you stop maintaining it.

## Optional: wrapper image

Use `optional/wrapper-image/` only when the upstream image cannot be installed from a template as-is, for example because it demands a secret that Unraid cannot generate. The wrapper is the upstream image plus one `COPY` of your entrypoint, built for amd64 and arm64 without emulation.

1. Move `Dockerfile`, `entrypoint.sh` and `scripts/*` to the repo root (`scripts/` merges with the validator), and `sync-upstream.yml` to `.github/workflows/`.
2. Fill the `TODO`s: upstream image, oldest supported upstream tag, the upstream entrypoint and `CMD` (from `docker inspect <image>`), and the one thing your entrypoint does.
3. Make `scripts/smoke-test.sh` test exactly that thing. The sync workflow refuses to publish a tag whose smoke test fails and opens an issue instead.
4. In the template set `<Repository>` to `ghcr.io/unraid-apps/<appname>:latest`.
5. After the first successful run: GitHub → Packages → the new package → settings → **Change visibility → Public**, and link it to the repo. Org settings → Actions → General must allow workflows to write packages.

How the sync works: every 6 hours `scripts/upstream-versions.py` lists the upstream image's stable `vX.Y.Z` tags at or above `MIN_UPSTREAM_VERSION`, compares manifest digests with `versions.json`, and schedules what is missing or changed. Each scheduled tag is built for amd64, smoke-tested, then built for amd64+arm64 and pushed under the same tag; the newest also gets `latest`. `versions.json` and `VERSIONS.md` are committed afterwards, which also keeps GitHub from disabling the schedule after 60 days without commits. A change to `Dockerfile` or `entrypoint.sh` rebuilds the newest tag.

## Conventions

- One app per repo, repo name = app name in lowercase, default branch `main`.
- Everything in English: XML, README, log lines.
- `<Support>` is this repo's issues; `<Project>` is upstream. App bugs are routed upstream via the issue chooser.
- Extra parameters: `--hostname=<appname>`; add `--add-host=host.docker.internal:host-gateway` when the app may need to reach services on the Unraid host.
- Tailscale fields pre-filled with `TailscaleEnabled=false`, mode `serve`, never `funnel`.
- No `--privileged`, no Docker socket, unless the app cannot work without it (say so in `<Requires>`).

Maintained by [Hardskiller](https://github.com/Hardskiller). MIT licensed.
