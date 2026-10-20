#!/usr/bin/env bash
# Install this repo's skills, agents and config into Claude Code, OpenCode and Pi.
# Re-run any time: it re-links everything and prunes what was removed.
# Upstream skills are synced into skills/ separately, by each port-<repo> skill.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./install.sh [--dry-run] [--copy] [--no-herdr] [--uninstall]

  --dry-run    show what would change, touch nothing
  --copy       copy skills instead of symlinking them (default: symlink, so edits are live)
  --no-herdr   skip Herdr integrations
  --uninstall  remove everything this script installed

Targets: ~/.claude (Claude Code), ~/.config/opencode (OpenCode), ~/.agents (Pi, also read by OpenCode).
EOF
}

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGETS=claude,opencode,agents
dry=0 link=--link herdr=1 uninstall=0

while (($#)); do
  case $1 in
    --dry-run) dry=1 ;;
    --copy) link= ;;
    --no-herdr) herdr=0 ;;
    --uninstall) uninstall=1 ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
run() { if ((dry)); then echo "  [dry-run] $*"; else "$@"; fi; }
for dep in git python3; do command -v "$dep" >/dev/null || { echo "missing dependency: $dep" >&2; exit 1; }; done

# Links managed by this script: "<source in repo>|<destination>". Missing sources are skipped.
LINKS=(
  "config/AGENTS.md|$HOME/.claude/CLAUDE.md"
  "config/AGENTS.md|$HOME/.config/opencode/AGENTS.md"
  "config/AGENTS.md|$HOME/.pi/agent/AGENTS.md"
)

link_file() {
  local src=$REPO/$1 dest=$2
  [[ -e $src ]] || return 0
  if [[ -L $dest && $(readlink "$dest") == "$src" ]]; then return; fi
  if [[ -e $dest || -L $dest ]]; then
    echo "  skip  $dest (exists and is not managed by agent-setup)"
    return
  fi
  echo "  link  $dest -> $src"
  run mkdir -p "$(dirname "$dest")"
  run ln -s "$src" "$dest"
}

unlink_file() {
  local src=$REPO/$1 dest=$2
  if [[ -L $dest && $(readlink "$dest") == "$src" ]]; then
    echo "  rm    $dest"
    run rm "$dest"
  fi
}

if ((uninstall)); then
  say "Removing installed skills and agents"
  args=(--uninstall --target "$TARGETS")
  ((dry)) && args+=(--dry-run)
  python3 "$REPO/scripts/port.py" "${args[@]}"
  say "Removing links"
  for l in "${LINKS[@]}"; do unlink_file "${l%%|*}" "${l#*|}"; done
  exit 0
fi

say "Validating repository"
python3 "$REPO/scripts/check.py" --source "$REPO"

say "Skills and agents"
args=(--source "$REPO" --target "$TARGETS" --prune $link)
((dry)) && args+=(--dry-run)
out=$(python3 "$REPO/scripts/port.py" "${args[@]}")
grep -vE '^  (link|copy|write) ' <<<"$out" || true

if ((!dry)); then
  mkdir -p "$HOME/.config/agent-setup"
  echo "$REPO" >"$HOME/.config/agent-setup/repo"
fi

say "Links"
for l in "${LINKS[@]}"; do link_file "${l%%|*}" "${l#*|}"; done

if ((herdr)) && command -v herdr >/dev/null; then
  say "Herdr integrations"
  for agent in opencode pi claude; do
    if herdr integration status 2>/dev/null | grep -q "^$agent: installed"; then
      echo "  ok    $agent"
    else
      echo "  install $agent"
      run herdr integration install "$agent" >/dev/null
    fi
  done
fi

say "Done"
