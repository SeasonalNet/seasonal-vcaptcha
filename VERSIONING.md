# Software versioning

Git `vMAJOR.MINOR.PATCH` tags are the release version authority. A clean
tagged build gets its package version from setuptools-scm. Untagged builds
include the commit distance and revision. Images receive the same version,
revision, and build timestamp as OCI metadata. CI validates tag identity before
the tag-gated image publication job can run.

For local Docker Compose builds, supply identity from the checkout:

```sh
APP_VERSION="$(sh tools/version.sh)" \
APP_REVISION="$(sh tools/version.sh --revision)" \
APP_BUILD_DATE="$(sh tools/version.sh --timestamp)" \
docker compose build
```

Run `sh tools/test-version.sh` to test development and release-tag resolution
against an isolated Git history.
