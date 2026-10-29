"""Public diagnostics: never include exception strings, URLs or credentials."""
import socket
import ssl
from urllib.error import HTTPError, URLError


class DataError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def diagnostic(exc):
    if isinstance(exc, DataError):
        return {'code': exc.code, 'message': exc.message}
    if isinstance(exc, PermissionError):
        return {'code': 'storage_permission', 'message': 'Écriture refusée dans /data : vérifier les permissions du dossier data pour UID/GID 1000:1000 dans DSM.'}
    if isinstance(exc, HTTPError):
        return {'code': 'http_error', 'message': f'Le fournisseur de cours a retourné HTTP {exc.code}. Vérifier son accessibilité depuis le NAS et ses conditions d’accès.'}
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, ssl.SSLError):
        return {'code': 'tls_error', 'message': 'Connexion HTTPS non validée : vérifier la date du NAS et les certificats. Ne pas désactiver la vérification TLS.'}
    if isinstance(reason, socket.gaierror):
        return {'code': 'dns_error', 'message': 'Résolution DNS impossible : vérifier les paramètres DNS et l’accès Internet du conteneur.'}
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return {'code': 'network_timeout', 'message': 'Le fournisseur de cours ne répond pas dans le délai prévu. Nouvelle tentative automatique dans cinq minutes.'}
    if isinstance(exc, (URLError, ConnectionError)):
        return {'code': 'network_error', 'message': 'Connexion au fournisseur impossible : vérifier le réseau, le proxy éventuel et les sorties HTTPS du conteneur.'}
    if isinstance(exc, OSError):
        return {'code': 'storage_error', 'message': 'Erreur système ou stockage : vérifier le montage /data et l’espace disponible sur le NAS.'}
    return {'code': 'internal_error', 'message': 'Erreur interne non classée. Exécuter python -m bot.diagnose depuis le terminal du conteneur pour isoler la phase en échec.'}
