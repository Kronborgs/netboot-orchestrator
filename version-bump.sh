#!/bin/bash
# version-bump.sh - Bump version and create release

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VERSION_FILE="$SCRIPT_DIR/VERSION"

# Get current date
CURRENT_DATE=$(date +%Y-%m-%d)

# Read current version
CURRENT_VERSION=$(cat "$VERSION_FILE")
CURRENT_DATE_FROM_VERSION=$(echo $CURRENT_VERSION | cut -d'-' -f1-3)
CURRENT_V=$(echo $CURRENT_VERSION | grep -o 'V[0-9]*$' | sed 's/V//')

echo "Current version: $CURRENT_VERSION"
echo "Current date: $CURRENT_DATE"
echo "Current V number: $CURRENT_V"

# Check if we're on the same day
if [ "$CURRENT_DATE" = "$CURRENT_DATE_FROM_VERSION" ]; then
    # Increment V number
    NEW_V=$((CURRENT_V + 1))
else
    # New day, reset V to 1
    NEW_V=1
fi

NEW_VERSION="$CURRENT_DATE-V$NEW_V"

echo "New version: $NEW_VERSION"

# Update VERSION file
echo "$NEW_VERSION" > "$VERSION_FILE"

# Update README.md badge
sed -i "s/Release-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-V[0-9]\+/Release-$NEW_VERSION/" "$SCRIPT_DIR/README.md"
sed -i "s/Version**: [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-V[0-9]\+/Version**: $NEW_VERSION/" "$SCRIPT_DIR/README.md"
sed -i "s/Last Updated**: .*/Last Updated**: $CURRENT_DATE/" "$SCRIPT_DIR/README.md"

# Update CHANGELOG
CHANGELOG_DATE=$(date +"%B %d, %Y")
sed -i "/#.*\[\[Unreleased\]\]/i ## [$NEW_VERSION] - $CHANGELOG_DATE\n" "$SCRIPT_DIR/CHANGELOG.md"

# Git operations
git add VERSION README.md CHANGELOG.md
git commit -m "chore(release): bump version to $NEW_VERSION"
git tag -a "$NEW_VERSION" -m "Release version $NEW_VERSION"

echo ""
echo "✓ Version bumped to $NEW_VERSION"
echo ""
echo "Next steps:"
echo "1. Review changes: git log --oneline -5"
echo "2. Push: git push origin main && git push origin --tags"
echo "3. Create GitHub release from tag: https://github.com/Kronborgs/netboot-orchestrator/releases/new?tag=$NEW_VERSION"
