ROOT_PATH=$(dirname "$0")
DIST_PATH=$(readlink -f "$ROOT_PATH/../dist")

echo $DIST_PATH
pip wheel . --no-deps --wheel-dir=$DIST_PATH
