# Installation Espace-Image sur écran d’accueil (iPad/PC)

## Version moderne
1. Ouvrez l’URL principale dans Safari (iPad/iPhone) ou Chrome/Edge (PC).
2. Cliquez sur le bouton de partage (Safari) ou le menu (Chrome).
3. Sélectionnez « Ajouter à l’écran d’accueil ».
4. L’icône Espace-Image apparaîtra sur le bureau, ouvrant l’app en plein écran.

## Version legacy
1. Ouvrez l’URL `/legacy` dans le navigateur.
2. Répétez les étapes ci-dessus pour l’ajouter à l’écran d’accueil.

## Admin
1. Ouvrez l’URL `/admin` dans le navigateur.
2. Utilisez « Ajouter à l’écran d’accueil » comme pour les autres pages.
3. L’app admin ouvrira en mode standalone avec l'icône Espace-Image Admin.

## Fonctionnalités PWA
- Icône personnalisée
- Mode plein écran
- Fonctionne hors-ligne (cache statique)
- Service worker minimal

## Notes
- Testé sur iPad (Safari) et PC (Chrome/Edge).
- Pour une expérience optimale, utilisez la version moderne sur les appareils récents.

## Note — Conversion SVG → PNG (à faire plus tard)

Les icônes vectorielles `app/static/espaceimage-192.svg` et `app/static/espaceimage-512.svg` sont présentes.
Si vous voulez des PNG raster optimisés (pour compatibilité maximale), exécutez localement :

```bash
python3 -m pip install --user cairosvg
python3 -m cairosvg app/static/espaceimage-192.svg -o app/static/espaceimage-192.png -w 192 -h 192
python3 -m cairosvg app/static/espaceimage-512.svg -o app/static/espaceimage-512.png -w 512 -h 512
ls -la app/static/espaceimage-*
```

Note : l'environnement d'édition distant peut bloquer l'installation d'outils (erreur FS). Exécutez ces commandes sur votre machine locale si nécessaire.
