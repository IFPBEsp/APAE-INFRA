#!/usr/bin/env bash
# Resolve o plano de execução do workflow .github/workflows/ansible-apply.yml.
#
# Recebe somente valores escolhidos pelo GitHub (evento, ref e inputs de
# workflow_dispatch) e os converte em um plano fechado, definido neste arquivo.
# Nenhum valor de entrada é repassado ao ansible-playbook sem ter sido
# comparado com a allowlist abaixo: não há caminhos, comandos, refs Git ou
# inventários livres.
#
# Variáveis de entrada:
#   EVENT_NAME       push | workflow_dispatch
#   GIT_REF          referência da execução (precisa ser refs/heads/main)
#   INPUT_PLAYBOOK   perfil escolhido no disparo manual
#   INPUT_TAGS       conjunto de tags escolhido no disparo manual
#   INPUT_INVENTORY  inventário escolhido no disparo manual
#   ANSIBLE_DIR      diretório ansible/ (padrão: relativo a este script)
#
# Saídas (em $GITHUB_OUTPUT, quando definido, e sempre em stdout):
#   profile, inventory, environment, host, playbooks, health_checks, tags,
#   needs_vault
set -euo pipefail

ANSIBLE_DIR="${ANSIBLE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

fail() {
  echo "ERRO: $*" >&2
  exit 1
}

readonly PUSH_PROFILE="baseline"

playbooks_for_profile() {
  case "$1" in
    baseline) echo "prepare.yml hardening.yml" ;;
    check) echo "check.yml" ;;
    prepare) echo "prepare.yml" ;;
    hardening) echo "hardening.yml" ;;
    k3s-preflight) echo "k3s-preflight.yml" ;;
    k3s) echo "k3s-preflight.yml k3s.yml" ;;
    k3s-verify) echo "k3s-verify.yml" ;;
    argocd) echo "argocd.yml" ;;
    configure-runtime-tls) echo "configure-runtime-tls.yml" ;;
    *) return 1 ;;
  esac
}

health_checks_for_profile() {
  case "$1" in
    k3s | argocd) echo "check.yml k3s-verify.yml" ;;
    *) echo "check.yml" ;;
  esac
}

tags_for_selection() {
  local profile="$1" selection="$2"
  case "$selection" in
    todas) echo "" ;;
    *)
      : "$profile"
      return 1
      ;;
  esac
}

environment_for_inventory() {
  case "$1" in
    production) echo "production" ;;
    *) return 1 ;;
  esac
}

host_for_inventory() {
  case "$1" in
    production) echo "apae-prod" ;;
    *) return 1 ;;
  esac
}

playbook_needs_vault() {
  case "$1" in
    argocd.yml) return 0 ;;
    *) return 1 ;;
  esac
}

[ "${GIT_REF:-}" = "refs/heads/main" ] ||
  fail "aplicação permitida somente a partir de refs/heads/main (recebido: '${GIT_REF:-}')."

case "${EVENT_NAME:-}" in
  push)
    profile="$PUSH_PROFILE"
    tags_selection="todas"
    inventory="production"
    ;;
  workflow_dispatch)
    profile="${INPUT_PLAYBOOK:-}"
    tags_selection="${INPUT_TAGS:-}"
    inventory="${INPUT_INVENTORY:-}"
    ;;
  *)
    fail "evento não autorizado: '${EVENT_NAME:-}'."
    ;;
esac

playbooks="$(playbooks_for_profile "$profile")" ||
  fail "perfil de playbook não autorizado: '$profile'."
health_checks="$(health_checks_for_profile "$profile")"
tags="$(tags_for_selection "$profile" "$tags_selection")" ||
  fail "tags não autorizadas para o perfil '$profile': '$tags_selection'."
environment="$(environment_for_inventory "$inventory")" ||
  fail "inventário não autorizado: '$inventory'."
host="$(host_for_inventory "$inventory")"

inventory_file="$ANSIBLE_DIR/inventories/$inventory/hosts.yml"
[ -f "$inventory_file" ] || fail "inventário inexistente: inventories/$inventory/hosts.yml."

needs_vault="false"
for pb in $playbooks $health_checks; do
  [ -f "$ANSIBLE_DIR/playbooks/$pb" ] || fail "playbook inexistente: playbooks/$pb."
  if playbook_needs_vault "$pb"; then
    needs_vault="true"
  fi
done

emit() {
  printf '%s=%s\n' "$1" "$2"
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf '%s=%s\n' "$1" "$2" >>"$GITHUB_OUTPUT"
  fi
}

emit profile "$profile"
emit inventory "$inventory"
emit environment "$environment"
emit host "$host"
emit playbooks "$playbooks"
emit health_checks "$health_checks"
emit tags "$tags"
emit needs_vault "$needs_vault"
