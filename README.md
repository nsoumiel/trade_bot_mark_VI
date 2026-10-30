# Paper NAS

Prototype de recherche et de paper trading pour Synology DS218+ (Intel amd64), DSM 7.3, Container Manager. Aucun connecteur de courtier ni ordre réel. Python 3.12 standard, sans dépendance Python externe. Aucune utilisation de Yahoo Finance ni d'un PEA.

## Installation sur le NAS

1. Copier ce projet dans `/volume1/docker/paper-nas` (ou un autre dossier partagé). Dans ce dossier, copier `.env.example` vers `.env` sans écraser un fichier existant.
2. Dans `.env`, régler `NAS_IP` sur l'adresse IPv4 privée du NAS. Le défaut `127.0.0.1` limite l'accès au NAS lui-même. Renseigner localement `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`. Protéger ce fichier avec les permissions DSM ; ne pas le partager ni le commiter.
3. Créer le dossier `data` et donner en lecture/écriture à l'UID/GID 1000:1000 utilisés dans l'image. Par SSH, si approprié aux ACL du dossier : `mkdir -p data`, puis `sudo chown 1000:1000 data`. Ne pas appliquer cette commande à tout le dossier partagé.
4. Dans Container Manager > Projet, créer un projet à partir du dossier contenant `compose.yaml`, puis le construire et le démarrer. Alternative SSH dans ce dossier : `sudo docker compose up -d --build`.
5. Ouvrir le port 8080 à l'adresse privée du NAS depuis le réseau local. Le tableau doit afficher « Actualisé » et une date de séance récente. Le statut Docker « healthy » confirme seulement le serveur HTTP, pas les données financières.

Ne pas exposer le port à Internet, QuickConnect ou une redirection de routeur. Tableau sans authentification, prévu pour un réseau local de confiance. Autoriser les sorties HTTPS vers `data.alpaca.markets` et `www.ecb.europa.eu` et, pour les notifications, `api.telegram.org`. Ne jamais désactiver la vérification TLS. Le téléchargement initial peut prendre quelques minutes. Les erreurs réseau laissent visibles les dernières données avec un avertissement.

Les notifications ne sont envoyées qu'aux nouveaux trades et au premier arrêt de risque. Aucun secret Telegram n'est nécessaire pour démarrer. Aucun chatbot de commande entrante n'est implémenté. Les erreurs Telegram sont journalisées sans token ; pas de relance automatique ni garantie de livraison.

## Fonctionnement

Capital 10 000 EUR. Univers de recherche : SPY (actions US), IEF (obligations US), GLD (or). Cours quotidiens Alpaca en USD (flux IEX, ajustement des splits), divisés par le taux de référence USD par EUR de la BCE de la même date. Seules les dates communes sont conservées, sans inventer de taux les jours absents. IEX couvre une seule place de marché et ne représente pas le marché consolidé SIP. Les distributions ne sont pas réinvesties. Les ETF US ne constituent pas une recommandation d'achat et peuvent être inaccessibles à un particulier UE : une future utilisation réelle devra choisir et tester des équivalents UCITS/ETC disponibles chez le courtier.

Au premier démarrage, le compte commence à la dernière séance terminée disponible, avec 200 séances de préchauffage. Tous les six heures, les séances supplémentaires sont ajoutées ; aucune séance UTC en cours n'est utilisée. Les données déjà consommées sont figées. La stratégie choisit chaque début de mois l'instrument au meilleur rendement sur 63 séances, positif et au-dessus de sa moyenne sur 200 séances. Sinon elle reste en liquidités. Signaux calculés sur la séance précédente et exécution simulée à la clôture suivante. Investissement de 50 % du capital disponible à chaque changement d'instrument, sans levier ni vente à découvert ; pas de rééquilibrage si l'instrument reste le même.

Hypothèses : 1 EUR de frais par ordre, glissement de 0,10 % à l'achat et à la vente, fractions de parts autorisées et cash non rémunéré. Les frais réels, spreads et modalités de change devront être remplacés par ceux du courtier envisagé.

L'arrêt permanent se déclenche à 15 % de baisse depuis le plus haut du compte, pour garder une marge par rapport au souhait de 20 %. Il provoque une vente au cours disponible, puis aucune reprise automatique. **Il ne garantit pas une perte maximale de 20 %** : gaps, délais et erreurs de données peuvent dépasser le seuil.

Le compte et les rapports sont dans `data/account.json` et `data/report.json`. Sauvegarder le dossier `data` avant mise à jour. Arrêter le projet avant une sauvegarde cohérente. Un seul processus doit utiliser ce dossier. Pour mettre à jour : arrêter, sauvegarder, remplacer le code puis reconstruire. Un changement de taux fiscal ou de seuil après création du compte est refusé pour éviter de réécrire son historique ; archiver les données à l'arrêt si l'on souhaite explicitement un nouveau scénario.

## Évaluation et fiscalité : limites importantes

Le tableau affiche séparément le compte virtuel démarré maintenant et un backtest exploratoire sur environ cinq ans après préchauffage. Comparaison à SPY conservé, avec exposition de 100 % contre 50 % pour la stratégie ; ce n'est donc pas une comparaison à risque égal.

`TAX_RATE=0.30` est une **hypothèse de scénario modifiable, pas une confirmation du taux légal applicable**. Le calcul agrège les plus/moins-values réalisées en euros par année, conserve les pertes pendant dix ans et provisionne l'impôt estimé. Il le débite à la première séance de l'année suivante, convention simplifiée différente de la date réelle de paiement. La valeur nette de liquidation inclut la vente fictive des positions et son impôt estimé. Aucun impôt n'est prélevé sur chaque achat.

Dividendes/distributions, retenues étrangères, crédits d'impôt, revenus hors portefeuille, option au barème, contributions supplémentaires et situations particulières ne sont pas modélisés. La convention d'ajustement des historiques du fournisseur n'est pas certifiée. Les chiffres ne constituent donc **pas un rendement total après impôts fiable** et ne permettent pas encore de décider « ça vaut le coup ». Aucun backtest hors échantillon indépendant ni test avec données réelles n'est validé à ce stade. À compléter avant toute conclusion : données de rendement total auditées, frais du courtier, scénarios fiscaux validés, comparaison à risque comparable et période de validation future sans réglage rétrospectif. Aucun bénéfice promis sur cinq ans.

Pour un résident fiscal français, un trust étranger n'efface pas automatiquement les obligations françaises et peut ajouter déclarations, taxation spécifique et frais. Une société ou structure étrangère n'est pas une économie automatique. Faire étudier toute structure par un fiscaliste. La crypto n'est pas retenue par défaut : sa volatilité et sa fiscalité demandent une évaluation distincte.

## Développement et validation

Dans le checkout existant, sans créer de worktree :

```sh
python3 -m unittest discover -s tests -v
DATA_DIR=/tmp/paperbot-data python3 -m bot.app
```

Le serveur écoute sur le port 8080. Requêtes internes : `/health`, `/api/status`. Le premier ne valide que le serveur ; le second doit indiquer une actualisation réussie. L'historique CSV personnel est aussi utilisable pour la recherche : `python3 -m bot.backtest prix.csv --tax-rate 0.30`. Colonnes `date,SPY,IEF,GLD`, dates ISO strictement croissantes, prix en EUR positifs, au moins 201 lignes. Les données synthétiques des tests valident le logiciel, jamais la rentabilité.

### Configuration Alpaca

Stooq a été remplacé après des erreurs HTTP et des contrôles JavaScript à la place des CSV. L'application interroge uniquement `data.alpaca.markets` pour les données historiques IEX ; elle ne transmet aucun ordre à Alpaca, même au compte paper. La simulation reste locale.

Dans votre `.env` existant, conserver `APCA_API_KEY_ID` et `APCA_API_SECRET_KEY`. Ne jamais partager ces valeurs. Compose transmet désormais ces deux variables au conteneur. Pour un lancement Python direct, les exporter dans le shell : Python ne charge pas automatiquement `.env`.

Après mise à jour, arrêter et reconstruire/recréer le projet dans Container Manager, en préservant `.env` et `data`. Alternative SSH : `sudo docker compose up -d --build --force-recreate`. Un simple redémarrage ne recharge ni le code ni les variables Compose. Lancer ensuite `python -m bot.diagnose` dans le conteneur et vérifier « Actualisé » dans le tableau.

Autoriser HTTPS vers `data.alpaca.markets` et `www.ecb.europa.eu`, en conservant TLS. Les clés doivent autoriser les données historiques IEX ; aucun abonnement SIP n'est supposé. Les refus 401/403, données absentes ou formats invalides sont signalés explicitement.

Les données consommées d'un compte existant restent figées : seuls les jours suivants utilisent Alpaca/BCE. Ce compte mélange donc les anciennes et nouvelles sources ; le backtest utilise la nouvelle source. Pour une recherche indépendante, archiver les données à l'arrêt et choisir volontairement un nouveau dossier, sans supprimer l'ancien compte.

La validation cloud utilise des réponses simulées, car les clés de votre NAS n'y sont pas disponibles. L'accès réel aux données et le déploiement NAS restent à valider après reconstruction.

## Tableau vide ou actualisation échouée

Depuis la version avec diagnostics, le tableau indique un code et une explication sous le statut. Une nouvelle tentative a lieu après cinq minutes en cas d'échec (six heures après un succès). Aucun prix artificiel n'est utilisé pour remplir le tableau.

Pour mettre à jour un projet déjà installé : arrêter le projet dans Container Manager, sauvegarder `data`, remplacer les fichiers du code par ceux de GitHub sans écraser `.env` ni `data`, puis lancer l'action de construction/reconstruction de l'image et redémarrer le projet. Un simple redémarrage ne recharge pas le code copié dans l'image. Recharger ensuite la page du navigateur.

Dans Container Manager > Conteneur > paperbot > Terminal, lancer `python -m bot.diagnose` (ou ouvrir un terminal `/bin/sh`, puis lancer cette commande). Alternative SSH depuis le dossier du projet : `sudo docker compose exec paperbot python -m bot.diagnose`. Ce contrôle teste l'écriture dans /data, chaque instrument Alpaca, le change BCE et l'historique commun, sans transaction ni message Telegram. Il peut prendre plusieurs minutes en cas de timeouts. Les messages ne contiennent ni secrets, ni corps brut des réponses externes.

- `storage_permission` : donner à l'UID/GID 1000:1000 l'accès en écriture au dossier `data` via les permissions/ACL DSM. Ne pas modifier tout le dossier partagé ni supprimer le compte.
- `dns_error`, `network_error`, `network_timeout` : vérifier l'accès Internet, les DNS et les sorties HTTPS du conteneur.
- `tls_error` : vérifier l'heure du NAS et ses certificats ; conserver la validation TLS.
- `http_error`, `provider_format`, `provider_empty`, `provider_access` : le fournisseur ne livre pas les données attendues. Une clé ou un autre fournisseur peut être nécessaire selon sa réponse ; le bot ne contourne pas les restrictions d'accès.
- `history_short` ou `history_stale` : historique incomplet ou trop ancien ; le compte attend des cours valides.
- `settings_changed` : rétablir les paramètres du compte existant ; ne pas effacer `data` pour traiter un problème réseau.

Le problème précis rencontré sur un NAS ne peut pas être déduit du seul statut générique de la première version. Partager le code et le message du diagnostic permet de choisir la correction adaptée.

### Terminal Synology : « Aucun terminal de télétype trouvé »

Le projet active maintenant `tty: true` et `stdin_open: true` pour allouer un pseudo-terminal. Après modification de `compose.yaml`, recréer le conteneur via le projet Container Manager (arrêter puis reconstruire/redéployer le projet). Un simple redémarrage du conteneur existant ne change pas ces options. Préserver `.env` et `data`.

Dans l'onglet Terminal, choisir la création/l'exécution d'une commande et saisir `/bin/sh`. Le processus principal est Python : s'y attacher directement n'ouvre pas un shell. Une fois le shell ouvert, lancer `python -m bot.diagnose`. Ne pas activer le mode privilégié. Alternative SSH : `sudo docker compose exec paperbot /bin/sh` depuis le dossier du projet.

En cas d'échec HTTP, le tableau affiche aussi le symbole concerné, sans nécessiter de terminal.
