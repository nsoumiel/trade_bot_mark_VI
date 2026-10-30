# Validation du prototype — 28 octobre 2026

- Python 3.12 : 8 tests exécutés et réussis (signaux décalés, arrêt permanent, frais, impôt de liquidation, absence de réécriture par données futures, données invalides, persistance et paramètres figés).
- HTTP local : `/`, `/health`, `/api/status` répondent 200 ; rapport synthétique cohérent.
- Docker : image construite ; démarrage en UID 1000 avec système de fichiers en lecture seule et /tmp temporaire ; requête fonctionnelle et actualisations répétées sans transaction dupliquée réussies.
- Données réelles : non validées, téléchargement Stooq refusé HTTP 403 par la politique cloud. Aucun résultat de performance historique réelle produit.
- Telegram : appels simulés dans les tests ; aucun message réel envoyé, aucun secret fourni.
- NAS : procédure préparée pour DS218+, DSM 7.3 / Container Manager ; installation sur le matériel non exécutée.
- Brouillon cloud enregistré : install_script, start_skill, accès stooq.com et api.telegram.org. Activation/publication non effectuées.

Ce prototype ne prouve pas une rentabilité après fiscalité. Voir les limites sur les distributions, l'ajustement des cours et l'absence de validation indépendante dans README.md.

## Migration Alpaca — 30 octobre 2026

- 17 tests réussis : en-têtes d’authentification, flux IEX, pagination, refus d’accès sans fuite de secrets, JSON invalide, change BCE, conversion EUR et exclusion du jour courant ; persistance et moteur toujours validés.
- Les trois anciens tests du lecteur CSV Stooq sont remplacés par les tests Alpaca/BCE.
- Les clés du NAS ne sont pas disponibles dans le cloud : aucun accès Alpaca authentifié réel ni déploiement NAS validé. Aucun ordre ni message Telegram envoyé.
- Documentation officielle Alpaca inaccessible depuis la politique réseau cloud (HTTP 403) ; le contrat du connecteur doit aussi être confirmé par le diagnostic réel sur NAS.
