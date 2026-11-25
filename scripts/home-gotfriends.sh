#!/bin/zsh
# Runs on your own computer, hourly: GotFriends blocks cloud servers but not home connections.
# Fetches GotFriends' public executive pages and pushes local/gotfriends.json for the
# morning cloud run. Commits only that file. Read only on the web.
set -e
cd "${0:A:h}/.."
git pull -q --ff-only
python3 -I collect.py --gotfriends-only local/gotfriends.json >/dev/null
git add local/gotfriends.json
git diff --cached --quiet && exit 0
git commit -q -m "gotfriends from home" -- local/gotfriends.json
git push -q
echo "gotfriends: pushed"
