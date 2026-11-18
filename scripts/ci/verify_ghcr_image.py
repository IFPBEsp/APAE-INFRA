import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request

MEDIA_TYPES = (
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.docker.distribution.manifest.v2+json",
)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    # Credenciais só podem ser enviadas aos endpoints fixos do GHCR.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def verify_published_image(image, tag, expected_digest, username="", password=""):
    repository = image.removeprefix("ghcr.io/")
    query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    token_url = "https://ghcr.io/token?" + query
    manifest_url = f"https://ghcr.io/v2/{repository}/manifests/{tag}"
    opener = urllib.request.build_opener(NoRedirect())

    def get(url, headers, limit):
        request = urllib.request.Request(url, headers=headers)
        with opener.open(request, timeout=30) as response:
            body = response.read(limit + 1)
            if len(body) > limit:
                raise ValueError("Resposta do GHCR excede o limite permitido.")
            return body, response.headers

    def fetch_manifest(authenticated):
        headers = {"Accept": "application/json"}
        if authenticated:
            basic = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = "Basic " + basic
        body, _ = get(token_url, headers, 1024 * 1024)
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Resposta de autenticação inválida do GHCR.")
        token = payload.get("token") or payload.get("access_token")
        if not isinstance(token, str) or not token or any(c in token for c in "\r\n"):
            raise ValueError("Token de leitura ausente ou inválido na resposta do GHCR.")
        return get(manifest_url, {
            "Accept": ", ".join(MEDIA_TYPES),
            "Accept-Encoding": "identity",
            "Authorization": "Bearer " + token,
        }, 8 * 1024 * 1024)

    try:
        body, headers = fetch_manifest(False)
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403) or not username or not password:
            raise
        error.close()
        body, headers = fetch_manifest(True)

    content_type = headers.get("Content-Type", "").split(";", 1)[0].strip()
    if content_type not in MEDIA_TYPES or headers.get("Content-Encoding", "identity") != "identity":
        raise ValueError("Tipo de objeto ou codificação não suportados na resposta do GHCR.")
    manifest = json.loads(body)
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 2:
        raise ValueError("Manifest publicado inválido.")
    if manifest.get("mediaType", content_type) != content_type:
        raise ValueError("Media type do manifest diverge do cabeçalho do GHCR.")
    # Hash dos bytes originais do objeto da tag, sem selecionar uma plataforma.
    # Para multiarch, compara o índice completo, não um manifest filho.
    actual_digest = "sha256:" + hashlib.sha256(body).hexdigest()
    if headers.get("Docker-Content-Digest", actual_digest) != actual_digest:
        raise ValueError("Cabeçalho de digest do GHCR diverge do conteúdo recebido.")
    if actual_digest != expected_digest:
        raise ValueError("Digest informado não corresponde ao objeto publicado para a tag.")

def main():
    try:
        username = os.environ.get("GHCR_READ_USERNAME", "")
        password = os.environ.get("GHCR_READ_TOKEN", "")
        if bool(username) != bool(password):
            raise ValueError("Configure GHCR_READ_USERNAME e GHCR_READ_TOKEN em conjunto.")
        verify_published_image(
            os.environ["IMAGE"], os.environ["IMAGE_TAG"], os.environ["IMAGE_DIGEST"],
            username or os.environ.get("REGISTRY_USERNAME", ""),
            password or os.environ.get("REGISTRY_TOKEN", ""),
        )
    except urllib.error.HTTPError as error:
        # Não registrar corpo, headers, tokens ou mensagens fornecidas pelo registro.
        print(f"::error::Consulta ao GHCR falhou (HTTP {error.code}). Verifique a tag e o acesso de leitura.")
        error.close()
        return 1
    except (OSError, ValueError, KeyError):
        print("::error::Falha ao verificar a imagem no GHCR: conexão, resposta, credenciais ou digest inválidos.")
        return 1
    print("Tag existente e digest do objeto publicado confirmados no GHCR.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
