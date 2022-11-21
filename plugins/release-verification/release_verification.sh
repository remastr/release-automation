### PARSE POSITIONAL ARGUMENTS
VERSION=$1

### VARIABLES SETUP

# Changelog for all commits merged to this branch since last commit on this branch
echo "Creating changelog"
CHANGELOG=$(git --no-pager log --format="%h  %s (%an)" --no-merges "origin/$GIT_BRANCH..HEAD")
echo $CHANGELOG

### FLOW

# Check if remote tag with given version already exists
if git ls-remote --tags origin | grep "v$VERSION"; then
    echo "Tag v$VERSION already exists, cannot release this version"
    exit 1
fi

# wget "https://raw.githubusercontent.com/remastr/release-automation/$RA_VERSION/plugins/release-verification/release_verification_plugin.py"
# python3 release_verification_plugin.py "$VERSION" "$CHANGELOG"