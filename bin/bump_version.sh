#!/bin/bash
set -e

# Check if git working tree is clean
if [[ -n $(git status --porcelain) ]]; then
  echo "Error: You have uncommitted changes. Please commit or stash them before releasing."
  exit 1
fi

# Release part: major, minor, patch (default: patch)
PART=$1
if [[ "$PART" == "" ]]; then
  PART="patch"
fi

# Get the last tag, e.g. v1.2.3
TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.1.0")

# Remove leading "v"
VER=${TAG#v}

# Split version into parts
IFS='.' read -r MAJOR MINOR PATCH <<< "$VER"

case $PART in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    ;;
  *)
    echo "Unknown part: $PART"
    exit 1
    ;;
esac

NEW_TAG="v$MAJOR.$MINOR.$PATCH"

echo "Current tag: $TAG"
echo "New tag: $NEW_TAG"

# Create commit and tag
git add .
git commit --allow-empty -m "Release $NEW_TAG"
git tag $NEW_TAG
git push origin main --tags

echo "Release done!"
