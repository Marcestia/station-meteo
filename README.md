# Station météo

Application Flask de tableau de bord météo.

## Déploiement Vercel

Le projet est configuré pour Vercel via `vercel.json` et l'entrée serverless `api/index.py`.

### Variables d'environnement

À configurer dans Vercel :

- `STORMGLASS_API_KEY` : clé API StormGlass utilisée pour les prévisions de houle.
- `STORMGLASS_CACHE_FILE` *(optionnel)* : chemin du cache StormGlass. Par défaut, l'application utilise `/tmp/stormglass_cache.json`, compatible avec le filesystem temporaire des fonctions serverless Vercel.
- `ENABLE_HEAVY_MODELS` *(optionnel)* : mettre `1` uniquement si tu veux réactiver GFS et Meteostat. Sur Vercel, laisse cette variable vide pour éviter les imports lourds et les appels réseau longs dans la fonction serverless.

### Déploiement

Depuis la racine du dépôt :

```bash
vercel
```

Puis, pour publier en production :

```bash
vercel --prod
```
