#!/usr/bin/env bash
set -euo pipefail

validated_commit=$(git rev-parse HEAD)
build_revision=$(git rev-parse --short HEAD)
release_dir=$(mktemp -d)
trap 'git worktree remove --force "$release_dir" >/dev/null 2>&1 || rmdir "$release_dir"' EXIT
release_ref=refs/heads/release

[[ -s dist/go1f-surf.conf && -s dist/ads.list ]]
existing_release=$(git ls-remote origin "$release_ref")
if [[ -n "$existing_release" ]]; then
    git fetch --no-tags origin "$release_ref"
    git worktree add --detach "$release_dir" FETCH_HEAD
    git -C "$release_dir" rm -qr -- .
else
    git worktree add --detach "$release_dir" HEAD
    git -C "$release_dir" switch --orphan shadowrocket-release-build
fi

# Copy only documented public assets. The personal build directory is never read here.
cp dist/go1f-surf.conf dist/ads.list "$release_dir/"
# Keep existing import URLs working with the same configuration.
cp dist/go1f-surf.conf "$release_dir/surf.conf"
cp dist/go1f-surf.conf "$release_dir/surf-offline.conf"
mkdir -p "$release_dir/modules"
cp dist/modules/splash-*.srmodule "$release_dir/modules/"
git -C "$release_dir" add --all

if git -C "$release_dir" diff --cached --quiet; then
    echo 'Publication already contains this build.'
    exit 0
fi

if [[ -n "${PUBLISH_SOURCE_BRANCH:-}" ]]; then
    upstream=$(git ls-remote --exit-code origin "refs/heads/$PUBLISH_SOURCE_BRANCH")
    if [[ "${upstream%%$'\t'*}" != "$validated_commit" ]]; then
        echo 'The default branch advanced after validation. Skipping this build.'
        exit 0
    fi
fi

git -C "$release_dir" -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit -m "Publish rules from $build_revision"
git -C "$release_dir" push origin "HEAD:$release_ref"
