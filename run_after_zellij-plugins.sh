#!/usr/bin/env bash
set -euo pipefail
bash "$(chezmoi source-path)/setup/scripts/executable_zellij-plugins.sh"
bash "$(chezmoi source-path)/setup/scripts/executable_zellij-workspace-bar.sh"
