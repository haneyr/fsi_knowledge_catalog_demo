# Releasing

How code gets from a branch to production, and the rules that keep that safe.

## The one rule

`main` is always releasable. Anything merged to `main` must be safe to ship to
production at any time. This is the invariant the whole workflow depends on — if
it holds, releasing is just tagging, and most of the painful release mechanics
go away.

The corollary: large, in-progress efforts do not sit unfinished in `main`. A
half-built feature in `main` means you can no longer tag a quick fix without also
shipping the unfinished work, which forces fragile hotfix gymnastics (see the
emergency hotfix section, which exists precisely for when this rule was broken).

## Where work happens

Small, shippable changes (bug fixes, small features, copy/UI tweaks) go straight
to `main` via PR. They're releasable on merge, by definition.

Large or multi-PR efforts (a UI redesign, an agent rearchitecture, a data-model
change) stay on a feature branch until they're actually ready to ship. While in
progress they get reviewed and validated on a preview/dev deploy, not in `main`.
They merge to `main` only when you intend them to go out in the next release.

If you genuinely need a big change to live in `main` before it's ready (to avoid
a long-lived branch), put it behind a runtime flag that is off in production, so
`main` stays releasable with the feature dark.

## Environments

- dev (`fsi-kc-demo-dev`): auto-deploys from `main` on every push (path-scoped
  triggers for website and each agent). This is the integration environment —
  expect it to run the bleeding edge.
- prod (`fsi-kc-demo-prod`): deploys only from version tags (`vX.Y.Z`) via the
  release pipeline. Prod runs the last tagged release, not `main`.

Use dev (or a dedicated preview deploy of a feature branch) to validate big work
before it reaches `main`.

## Releasing to production

1. Make sure `main` is green on dev and contains only what you intend to ship.
2. Tag it: `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The release pipeline (`cloudbuild-release.yaml`) verifies the tag is on `main`,
   then deploys agents and the website to prod.
4. Verify the release actually landed (see below). Do not trust a green build
   alone.

Release small and often. The cost of a release should be boring. When prod sits
many commits behind `main`, each release becomes a large, scary diff, which makes
you release less, which makes the next diff bigger. Keeping prod close to `main`
is the cheapest way to keep releases low-risk.

## Verifying a release

A green build does not prove the deploy happened — a deploy step can fail and
still report success if its errors are swallowed. After any prod release, confirm
the live state directly:

- The serving Cloud Run revision is new (`gcloud run services describe
  fsi-kc-demo-ui-live --project=fsi-kc-demo-prod --region=us-central1
  --format='value(status.latestReadyRevisionName)'`).
- A known marker from the change is present in the served asset (e.g. curl the
  static file and grep for the new code).
- OAuth and the agents still respond (`/api/config`).

## Emergency hotfix (when `main` is not releasable)

This is the escape hatch for when prod needs a fix but `main` contains unreleased
work. Needing it routinely is a signal that the "main is always releasable" rule
has slipped — fix that rather than leaning on this.

1. Branch from the last release tag: `git checkout -b release/vX.Y.Z+1 vX.Y.Z`.
2. Cherry-pick the fix commits from `main` (they must already be merged to `main`
   — the release pipeline only promotes commits that exist on `main`, verified by
   patch-id with `git cherry`). Cherry-picks must apply with their original diff
   intact; if resolving a conflict changes the patch, the pipeline will reject the
   tag as "not on main."
3. Tag and push: `git tag vX.Y.Z+1 && git push origin vX.Y.Z+1`.
4. Verify as above.

## Don't make imperative changes to prod

Anything configured by hand (`gcloud run services update`, ad-hoc IAM grants)
will drift and eventually break a release the way the Cloud Run scaling flags and
the deployer service-account IAM both did. Put configuration in code:

- Cloud Run service settings belong in `website-live/deploy.sh`.
- Deployer service-account IAM belongs in Terraform (see the open issue on moving
  it out of the manual `docs/ci-setup.md` runbook).
- Secrets belong in Secret Manager and are read by the pipeline, not passed by
  hand.

If you must touch prod live to stop a fire, codify the same change immediately so
the next release doesn't undo it.
