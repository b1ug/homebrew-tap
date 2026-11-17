# nb1 tap preparation

- The user approved completing the formal tap and publishing the documentation site on 2026-11-17. The root agent controls repository visibility and remote publication after review.
- The product is nb1; the hardware is blink(1).
- A Formula is generated only from a verified published upstream release into
  an explicitly selected new local review directory. A verified production Formula
  and its release input/provenance may then be committed for publication. Keep
  materialized archives and temporary review outputs out of the repository;
  synthetic fixture data belongs only inside automated tests.
- Reuse the verified release's renderer/template. Do not add a second Formula
  implementation, synthetic install channel or automatic publishing/service step.
- Unit tests remain offline with mock HTTP. Native installation CI uses fresh
  hosted runners and the published source archive. Local acceptance uses only
  owned Homebrew prefixes/containers, never global Homebrew or existing services.
  No test requires physical USB. Public docs default to English, with Chinese
  alongside them.

# v0.1.0 packaging corrections

- Native source-install acceptance exposed Go recording Homebrew's enclosing
  Git commit in nb1's build metadata. The user-authorized formal publication
  includes a reviewed packaging-only exception: after the verified released
  renderer, apply four exact corrections only to version 0.1.0, source
  `535621a689e5a9e35c5e897aadcd4b023d2f157b` and upstream Formula SHA-256
  `fa9e7a34f85f3a734f8bbc953fc878aab6d922e7da0479732ab61fd9df91bb1c`.
- Disable automatic parent-repository VCS detection; retain the explicit nb1
  source commit linker field. The other three changes only satisfy strict
  Homebrew style. Record original/output hashes and each reason in provenance.
- Future releases do not receive this adapter. Do not add a generic patch
  engine, a second Formula renderer, a new dependency, or alter published tags,
  core code or foundation versions to make a packaging check pass.
