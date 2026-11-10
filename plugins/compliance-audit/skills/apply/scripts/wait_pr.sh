#!/usr/bin/env bash
# Poll a PR until it needs attention. Run in the background; the exit code says why it stopped.
# Usage: wait_pr.sh <pr-number-or-url> [interval-seconds=60] [max-hours=6] [required-status-context]
#   0  merged
#   10 branch is behind or conflicts with base (BEHIND / DIRTY) -> merge base in, push, rerun
#   20 PR closed without merging
#   30 a check failed (names on stdout)
#   40 still open after max-hours (e.g. waiting on a required review)
#   50 head commit has no successful <required-status-context> status (only when that arg is given)
set -u
pr=$1; iv=${2:-60}; deadline=$(( $(date +%s) + ${3:-6} * 3600 )); need=${4:-}
q='[.state, .mergeStateStatus,
    ("," + ([.statusCheckRollup[]? | select((.conclusion // .state // "") == "SUCCESS") | (.name // .context)] | join(",")) + ","),
    ([.statusCheckRollup[]? | select((.conclusion // .state // "") as $c
      | $c == "FAILURE" or $c == "ERROR" or $c == "CANCELLED" or $c == "TIMED_OUT" or $c == "ACTION_REQUIRED")
      | (.name // .context)] | join(","))] | @tsv'
while :; do
  if out=$(gh pr view "$pr" --json state,mergeStateStatus,statusCheckRollup --jq "$q" 2>&1); then
    IFS=$'\t' read -r state merge ok failed <<<"$out"
    case $state in
      MERGED) echo merged; exit 0 ;;
      CLOSED) echo "closed without merge"; exit 20 ;;
    esac
    [ -n "$failed" ] && { echo "checks failed: $failed"; exit 30; }
    case $merge in BEHIND|DIRTY) echo "$merge"; exit 10 ;; esac
    [ -n "$need" ] && [[ $ok != *",$need,"* ]] && { echo "missing status: $need"; exit 50; }
  else
    echo "gh error (retrying): $out" >&2
  fi
  [ "$(date +%s)" -ge "$deadline" ] && { echo "timeout: state=${state:-?} merge=${merge:-?}"; exit 40; }
  sleep "$iv"
done
