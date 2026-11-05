#!/usr/bin/env bash
# Validacao estatica do Ansible. Usado pelo CI (.github/workflows/ansible-ci.yml)
# e localmente, para que ambos executem exatamente os mesmos comandos.
#
# Uso (a partir da raiz do repositorio):
#   ansible/scripts/validate.sh [all|secrets|collections|yaml|lint|syntax]
#
# Nunca conecta em hosts: --syntax-check e ansible-inventory --list nao abrem SSH.
set -euo pipefail

ANSIBLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ANSIBLE_DIR"

export ANSIBLE_COLLECTIONS_PATH="$ANSIBLE_DIR/.collections"
export ANSIBLE_HOST_KEY_CHECKING="False"
export ANSIBLE_RETRY_FILES_ENABLED="False"
# Inventario ilegivel deve falhar (por padrao o Ansible so emite aviso e segue).
export ANSIBLE_INVENTORY_ANY_UNPARSED_IS_FAILED="True"
export ANSIBLE_NOCOLOR="1"

log() { printf '\n==> %s\n' "$*"; }

has_playbooks() {
  compgen -G "playbooks/*.yml" >/dev/null || compgen -G "playbooks/*.yaml" >/dev/null
}

ansible_content_paths() {
  local path
  for path in playbooks roles inventories collections; do
    [ -d "$path" ] || continue
    if find "$path" -type f \( -name '*.yml' -o -name '*.yaml' \) -print -quit | grep -q .; then
      printf '%s\n' "$path"
    fi
  done
}

has_ansible_content() {
  [ -n "$(ansible_content_paths)" ]
}

check_secrets() {
  log "Verificando ausencia de chaves privadas versionadas"
  if grep -R -I -n -E -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
      --exclude-dir=.collections --exclude-dir=.cache --exclude=validate.sh . ; then
    echo "ERRO: chave privada encontrada em ansible/. Remova e rotacione a credencial." >&2
    return 1
  fi
}

check_collections() {
  log "Validando versoes fixadas em requirements.yml"
  python3 - <<'PY'
import re
import sys

import yaml

with open("requirements.yml", encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}

problems = []
for item in data.get("collections") or []:
    if isinstance(item, str):
        item = {"name": item}
    name = item.get("name", "<sem nome>")
    version = str(item.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problems.append(f"{name}: versao exata obrigatoria (X.Y.Z), encontrado '{version}'")

for key in ("roles",):
    if data.get(key):
        problems.append(f"'{key}' externos nao sao permitidos sem versao fixada e revisao")

if problems:
    print("\n".join(f"ERRO: {p}" for p in problems), file=sys.stderr)
    sys.exit(1)
print("OK")
PY

  if python3 -c "import sys,yaml; d=yaml.safe_load(open('requirements.yml')) or {}; sys.exit(0 if d.get('collections') else 1)"; then
    log "Instalando collections fixadas"
    ansible-galaxy collection install -r requirements.yml -p "$ANSIBLE_COLLECTIONS_PATH"
  else
    echo "Nenhuma collection declarada; nada a instalar."
  fi
}

check_yaml() {
  log "yamllint"
  yamllint --strict -c .yamllint .
}

check_lint() {
  local -a content_paths=()
  mapfile -t content_paths < <(ansible_content_paths)
  if ! has_ansible_content; then
    echo "Nenhum conteudo Ansible aplicavel; ansible-lint ignorado."
    return 0
  fi
  log "ansible-lint"
  ansible-lint --config-file .ansible-lint "${content_paths[@]}"
}

check_syntax() {
  local playbooks_present=true
  local -a inventories=()
  has_playbooks || playbooks_present=false
  for inv in inventories/*/; do
    [ -d "$inv" ] || continue
    for f in "$inv"hosts.yml "$inv"hosts.yaml; do
      [ -f "$f" ] && inventories+=("$f")
    done
  done

  if [ "$playbooks_present" = true ] && [ "${#inventories[@]}" -eq 0 ]; then
    echo "ERRO: playbooks existem, mas nenhum inventories/<ambiente>/hosts.yml foi encontrado." >&2
    return 1
  fi

  for inv in "${inventories[@]}"; do
    log "ansible-inventory --list: $inv"
    ansible-inventory -i "$inv" --list >/dev/null

    [ "$playbooks_present" = true ] || continue
    for pb in playbooks/*.yml playbooks/*.yaml; do
      [ -f "$pb" ] || continue
      log "ansible-playbook --syntax-check: $pb ($inv)"
      ansible-playbook -i "$inv" --syntax-check "$pb"
    done
  done

  if [ "$playbooks_present" = false ]; then
    echo "Nenhum playbook em ansible/playbooks/; syntax-check ignorado."
  fi
}

case "${1:-all}" in
  secrets) check_secrets ;;
  collections) check_collections ;;
  yaml) check_yaml ;;
  lint) check_lint ;;
  syntax) check_syntax ;;
  all)
    check_secrets
    check_collections
    check_yaml
    check_lint
    check_syntax
    ;;
  *)
    echo "Uso: $0 [all|secrets|collections|yaml|lint|syntax]" >&2
    exit 2
    ;;
esac
