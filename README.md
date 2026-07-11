# Wine Stock Watcher

Surveille des fiches produit Shopify (Peak Wines, etc.) et envoie un e-mail
uniquement quand quelque chose change : passage en low stock, rupture,
retour en stock, ou baisse de prix.

## Mise en place (5 min)

### 1. Créer un webhook Discord
1. Ouvre Discord, crée un serveur perso si tu n'en as pas déjà un (icône "+"
   en bas à gauche → "Créer un serveur").
2. Crée un salon dédié, par ex. `#wine-alerts`.
3. Clique sur l'icône ⚙️ du salon → **Intégrations** → **Webhooks** →
   **Nouveau webhook**.
4. Donne-lui un nom (ex. "Wine Stock Bot"), puis clique sur
   **Copier l'URL du webhook**.
5. Garde cette URL de côté (elle ressemble à
   `https://discord.com/api/webhooks/123456789/xxxxxxxxxxxx`) — ne la
   partage jamais publiquement, elle permet d'écrire dans ton salon.

### 2. Créer le repo GitHub
1. Crée un nouveau repo (ex: `wine-stock-watcher`), ou ajoute ces fichiers
   dans un dossier de ton repo existant `Vabelgian/Cave-a-vin`.
2. Pousse tous les fichiers de ce dossier.

### 3. Ajouter le secret GitHub
Dans le repo → **Settings → Secrets and variables → Actions → New repository secret** :
- `DISCORD_WEBHOOK_URL` → l'URL copiée à l'étape 1

### 4. Compléter config.yaml
Remplace les URLs `REMPLACE_MOI` par les vraies fiches produit
(clic droit → copier le lien sur le site, tu peux retirer les `?_pos=...`
en fin d'URL, ce n'est pas nécessaire).

### 5. Premier lancement
Va dans l'onglet **Actions** du repo → sélectionne "Check wine stock" →
**Run workflow** (bouton manuel). Ce premier passage sert uniquement à
enregistrer l'état initial (aucune notif n'est envoyée la première fois pour
chaque bouteille, il faut un point de comparaison).

Ensuite, le workflow tourne automatiquement toutes les 6h et t'écrit dans
`#wine-alerts` dès qu'un changement pertinent est détecté.

## Tester en local

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxx/yyy"
python watcher.py
```

## Notes
- Le statut est lu tel quel dans le texte de la page ("In stock", "Low
  stock", "Sold out") — pas de raisonnement IA, donc pas d'hallucination
  possible sur ce point.
- Fonctionne pour n'importe quelle fiche produit Shopify avec la même
  structure (Peak Wines et la plupart des shops vin Shopify). Si un site
  utilise une structure différente, il faudra adapter `STATUS_PATTERNS` et
  `PRICE_PATTERN` dans `watcher.py`.
- `state.json` est committé automatiquement par le workflow — c'est la
  mémoire du script entre deux exécutions.
