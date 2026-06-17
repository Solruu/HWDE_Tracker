#!/usr/bin/env python3
"""
translate_guide_descriptions.py
================================
Traduit en français les descriptions skull_1/skull_2 et search.desc
dans le bloc GUIDE d'un fichier HTML tracker HWDE.

USAGE sur une nouvelle map :
  1. Extraire les descriptions EN de la map :
       python3 translate_guide_descriptions.py --extract index.html > descriptions_to_translate.txt
  2. Remplir le dict TRANSLATIONS ci-dessous (ou utiliser l'API Claude)
  3. Appliquer :
       python3 translate_guide_descriptions.py --apply index.html > index_translated.html

AVEC L'API CLAUDE (méthode recommandée pour les nouvelles maps) :
  import anthropic, json
  client = anthropic.Anthropic()
  descs = [...]  # liste des descriptions EN
  msg = client.messages.create(
      model="claude-sonnet-4-6",
      max_tokens=4000,
      messages=[{
          "role": "user",
          "content": (
              "Traduis en français ces descriptions de missions/lieux du jeu "
              "Hyrule Warriors: Definitive Edition. Réponds UNIQUEMENT avec un "
              f"objet JSON {{\"EN\": \"FR\", ...}}:\n{json.dumps(descs)}"
          )
      }]
  )
  translations = json.loads(msg.content[0].text)
"""

import json, re, sys, argparse

# ── DICTIONNAIRE DE TRADUCTION ────────────────────────────────────────────────
# Clé = texte anglais exact, Valeur = traduction française
TRANSLATIONS = {
    # ── SKULLTULAS ─────────────────────────────────────────────────────────────
    "Complete first mission, KO 150 enemies with special attacks without losing — same location as #1":
        "Complétez la première mission, réalisez 150 KO avec des attaques spéciales sans perdre — même emplacement que la n°1",
    "Complete first mission, capture 5+ enemy keeps without losing (40% health) — same location as #1":
        "Complétez la première mission, capturez 5+ forts ennemis sans perdre (40% PV) — même emplacement que la n°1",
    "Complete first mission, capture 5+ enemy keeps without losing (dead end north of westernmost owl statue)":
        "Complétez la première mission, capturez 5+ forts ennemis sans perdre (impasse au nord de la statue hibou la plus à l'ouest)",
    "Complete first mission, capture 5+ enemy keeps without losing (tunnel between Rock Keep and central circular area)":
        "Complétez la première mission, capturez 5+ forts ennemis sans perdre (tunnel entre le Fort Rocheux et la grande zone circulaire)",
    "Complete first mission, capture 5+ enemy keeps without losing — same location as #1":
        "Complétez la première mission, capturez 5+ forts ennemis sans perdre — même emplacement que la n°1",
    "Complete the first mission and KO 150 enemies with special attacks without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1.":
        "Complétez la première mission et réalisez 150 KO avec des attaques spéciales sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "Complete the first mission and KO 150 enemies with special attacks without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1. \uf148":
        "Complétez la première mission et réalisez 150 KO avec des attaques spéciales sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "Complete the first mission and capture five enemy Keeps without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1.":
        "Complétez la première mission et capturez 5 forts ennemis sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "Complete the first mission and capture five or more Keeps without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1.":
        "Complétez la première mission et capturez 5 forts ou plus sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "Complete the first mission and capture five or more enemy Keeps without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1.":
        "Complétez la première mission et capturez 5 forts ennemis ou plus sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "Complete the first mission and capture five or more enemy keeps without losing (≤40% PV perdus). It is located in the same place as Gold Skulltula #1.":
        "Complétez la première mission et capturez 5 forts ennemis ou plus sans perdre (≤40% PV perdus). Même emplacement que la Skulltula d'Or n°1.",
    "KO 1000 enemies (NE Dragon Roost in the grass)":
        "Réalisez 1\u00a0000 KO (au NE du Perchoir du Dragon dans l'herbe)",
    "KO 1000 enemies (NE from Star Island Keep dead end)":
        "Réalisez 1\u00a0000 KO (au NE depuis l'impasse du Fort de l'Île Étoilée)",
    "KO 1000 enemies (NE of Dragon Roost)":
        "Réalisez 1\u00a0000 KO (au NE du Perchoir du Dragon)",
    "KO 1000 enemies (NW corner dead end)":
        "Réalisez 1\u00a0000 KO (impasse au coin NO)",
    "KO 1000 enemies (NW dead end from Enemy Base)":
        "Réalisez 1\u00a0000 KO (impasse au NO depuis la Base Ennemie)",
    "KO 1000 enemies (NW path from Allied Base — use hookshot)":
        "Réalisez 1\u00a0000 KO (chemin NO depuis la Base Alliée — Utilisez le Grappin)",
    "KO 1000 enemies (SE corner dead end)":
        "Réalisez 1\u00a0000 KO (impasse au coin SE)",
    "KO 1000 enemies (Switch: giant dead end in center; 3DS: under boulder east of West Keep)":
        "Réalisez 1\u00a0000 KO (Switch : grande impasse au centre ; 3DS : sous un rocher à l'est du Fort Ouest)",
    "KO 1000 enemies (Switch: hallway north entrance Temple Face Keep; 3DS: east of Central Hall)":
        "Réalisez 1\u00a0000 KO (Switch : couloir entrée nord du Fort de la Face du Temple ; 3DS : à l'est du Couloir Central)",
    "KO 1000 enemies (Switch: north wall inside empty room east of Allied Keep; 3DS: outside north wall West Field Keep)":
        "Réalisez 1\u00a0000 KO (Switch : mur nord dans la salle vide à l'est du Fort Allié ; 3DS : mur nord extérieur du Fort Ouest du Champ)",
    "KO 1000 enemies (behind cracked wall, west side of path between E. Boulder Keep and East Goron Keep)":
        "Réalisez 1\u00a0000 KO (derrière un mur fissuré, côté ouest du chemin entre le Fort des Rochers Est et le Fort Goron Est)",
    "KO 1000 enemies (east wall, large circular area)":
        "Réalisez 1\u00a0000 KO (mur est, grande zone circulaire)",
    "KO 1000 enemies (east wall, large circular room)":
        "Réalisez 1\u00a0000 KO (mur est, grande salle circulaire)",
    "KO 1000 enemies (middle of large open area south of Chief's Room)":
        "Réalisez 1\u00a0000 KO (milieu de la grande zone ouverte au sud de la Salle du Chef)",
    "KO 1000 enemies (north from SE owl statue)":
        "Réalisez 1\u00a0000 KO (au nord depuis la statue hibou SE)",
    "KO 1000 enemies (west of Enemy Base)":
        "Réalisez 1\u00a0000 KO (à l'ouest de la Base Ennemie)",
    "KO 1000 enemies. Located along the north wall of Bridge Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : le long du mur nord du Fort du Pont.",
    "KO 1000 enemies. Located along the north wall of the empty area east of Castle Keep. Located along the wall if you go north then west from the Castle Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : le long du mur nord de la zone vide à l'est du Fort du Château. Le long du mur en allant au nord puis à l'ouest depuis le Fort du Château.",
    "KO 1000 enemies. Located east of the Temple Square.":
        "Réalisez 1\u00a0000 KO. Emplacement : à l'est de la Place du Temple.",
    "KO 1000 enemies. Located in the dead end northeast from the East Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : dans l'impasse au nord-est du Fort Est.",
    "KO 1000 enemies. Located in the dead end south of the Central Square.":
        "Réalisez 1\u00a0000 KO. Emplacement : dans l'impasse au sud de la Place Centrale.",
    "KO 1000 enemies. Located just north of the S. Rockface Keep. Located next to the west entrance of the bridge southwest from Town Center Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : juste au nord du Fort de la Falaise Sud. À côté de l'entrée ouest du pont au sud-ouest du Fort du Centre-Ville.",
    "KO 1000 enemies. Located just outside the west exit of N. Entrance Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : juste à l'extérieur de la sortie ouest du Fort de l'Entrée Nord.",
    "KO 1000 enemies. Located north of the west entrance to the Stock Room.":
        "Réalisez 1\u00a0000 KO. Emplacement : au nord de l'entrée ouest du Magasin.",
    "KO 1000 enemies. Located northeast from South Field Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : au nord-est du Fort du Champ Sud.",
    "KO 1000 enemies. Located southeast from E. Boulder Keep.":
        "Réalisez 1\u00a0000 KO. Emplacement : au sud-est du Fort des Rochers Est.",
    "KO 1000 enemies. Located straight to the west from Crystal Cave at the cliff where you can jump down.":
        "Réalisez 1\u00a0000 KO. Emplacement : directement à l'ouest de la Grotte de Cristal, au bord de la falaise où l'on peut sauter.",
    "KO 1000 enemies. Located to the far west from the North Oasis.":
        "Réalisez 1\u00a0000 KO. Emplacement : très loin à l'ouest depuis l'Oasis Nord.",

    # ── SEARCHES ──────────────────────────────────────────────────────────────
    "Aim for the hookshot marker at the top of the screen":
        "Visez la cible du Grappin en haut de l'écran",
    "Blow up the rock in the river":
        "Faites exploser le rocher dans la rivière",
    "Bomb the eastern of the two bottom tiles on the west rock":
        "Bombez la tuile du bas la plus à l'est sur le rocher ouest",
    "Bomb the eastern of the two wall tiles just west of the long vertical part of the north wall":
        "Bombez la tuile de mur la plus à l'est parmi les deux, juste à l'ouest de la partie verticale du mur nord",
    "Bomb the easternmost of the top wall tiles before the diagonal by the west exit":
        "Bombez la tuile de mur supérieure la plus à l'est avant la diagonale près de la sortie ouest",
    "Bomb the fifth wall tile from the right on the top wall":
        "Bombez la 5e tuile de mur depuis la droite sur le mur supérieur",
    "Bomb the first solid wall tile on the north wall to the east of the large diamond shaped area of the path":
        "Bombez la 1ère tuile solide du mur nord à l'est de la grande zone en losange du chemin",
    "Bomb the first tile at the northeast end of the diagonal portion of the north wall":
        "Bombez la 1ère tuile à l'extrémité nord-est de la partie diagonale du mur nord",
    "Bomb the fourth tile from the right from the stairs.":
        "Bombez la 4e tuile depuis la droite à partir des escaliers.",
    "Bomb the fourth wall tile from the right on the upper wall":
        "Bombez la 4e tuile de mur depuis la droite sur le mur supérieur",
    "Bomb the middle of the three northwestern wall spaces":
        "Bombez le milieu des trois espaces de mur nord-ouest",
    "Bomb the only full wall tile northwest of the butterflies":
        "Bombez l'unique tuile de mur entière au nord-ouest des papillons",
    "Bomb the right of the two whole northern wall tiles between the slopes":
        "Bombez la droite des deux tuiles nord entières entre les pentes",
    "Bomb the rock in the lake":
        "Faites exploser le rocher dans le lac",
    "Bomb the rock in the water":
        "Faites exploser le rocher dans l'eau",
    "Bomb the second wall tile from the right by the east entrance":
        "Bombez la 2e tuile de mur depuis la droite près de l'entrée est",
    "Bomb the seventh wall tile from the left":
        "Bombez la 7e tuile de mur depuis la gauche",
    "Bomb the southeast full tile on the boulder.":
        "Bombez la tuile complète sud-est sur le rocher.",
    "Bomb the third wall tile from the left of the four tiles just west of the north exit":
        "Bombez la 3e tuile de mur depuis la gauche parmi les quatre juste à l'ouest de la sortie nord",
    "Bomb the wall tile 2nd from the right beside the north exit":
        "Bombez la 2e tuile de mur depuis la droite à côté de la sortie nord",
    "Bomb the wall tile on north wall directly between the eastern two columns of statues":
        "Bombez la tuile de mur nord directement entre les deux colonnes de statues est",
    "Bomb the wall tile two tiles east from the ladder":
        "Bombez la tuile de mur à deux cases à l'est de l'échelle",
    "Burn the fifth tree from the right":
        "Brûlez le 5e arbre depuis la droite",
    "Burn the northernmost of the five trees in a single row in the middle":
        "Brûlez l'arbre le plus au nord parmi les cinq en rangée au milieu",
    "Burn the single bush blocking the northern path":
        "Brûlez l'unique buisson bloquant le chemin nord",
    "Burn the southeast of the eight trees in the middle":
        "Brûlez l'arbre au sud-est parmi les huit arbres au milieu",
    "Burn the southeast of the four trees by the west entrance":
        "Brûlez l'arbre au sud-est parmi les quatre près de l'entrée ouest",
    "Burn the southeast of the four trees in the center":
        "Brûlez l'arbre au sud-est parmi les quatre au centre",
    "Burn the southeasternmost of the five trees by the west exit":
        "Brûlez l'arbre le plus au sud-est parmi les cinq près de la sortie ouest",
    "Burn the southern of the two green trees by the east exit.":
        "Brûlez le plus au sud des deux arbres verts près de la sortie est.",
    "Burn the southern of the two trees by the east entrance":
        "Brûlez le plus au sud des deux arbres près de l'entrée est",
    "Burn the southern of the two trees by the west entrance":
        "Brûlez le plus au sud des deux arbres près de l'entrée ouest",
    "Burn the southern of the two trees closest to the east exit":
        "Brûlez le plus au sud des deux arbres les plus proches de la sortie est",
    "Burn the southern of the two trees next to west entrance":
        "Brûlez le plus au sud des deux arbres près de l'entrée ouest",
    "Burn the southwest corner tree in the group of six trees.":
        "Brûlez l'arbre du coin sud-ouest dans le groupe de six arbres.",
    "Burn the third tree from the top on the left side of the straight path to the east":
        "Brûlez le 3e arbre depuis le haut sur le côté gauche du chemin droit vers l'est",
    "Burn the top tree on the east wall of trees":
        "Brûlez l'arbre du haut sur le mur est des arbres",
    "Burn the tree in the northwest corner.":
        "Brûlez l'arbre dans le coin nord-ouest.",
    "Dig the soft dirt":
        "Creusez la terre meuble",
    "Digging Mitts: Dig the soft dirt":
        "Gants de Fouille : Creusez la terre meuble",
    "North wall directly north from left tile of southern entrance":
        "Mur nord directement au nord de la tuile gauche de l'entrée sud",
    "Push the east statue":
        "Poussez la statue est",
    "Push the isolated rock in the western area":
        "Poussez le rocher isolé dans la zone ouest",
    "Push the middle statue in the top row":
        "Poussez la statue du milieu dans la rangée supérieure",
    "Push the northeasternmost statue":
        "Poussez la statue la plus au nord-est",
    "Push the sole rock":
        "Poussez l'unique rocher",
    "Push the statue in the first row, third column":
        "Poussez la statue en 1ère rangée, 3e colonne",
    "Push the tombstone in row two, column three":
        "Poussez la pierre tombale en rangée deux, colonne trois",
    "Push the western of the four stones in the middle":
        "Poussez la plus à l'ouest des quatre pierres au milieu",
    "Seventh wall tile from the left on north wall.":
        "7e tuile de mur depuis la gauche sur le mur nord.",
    "Shoot the ring of fire":
        "Tirez sur l'anneau de feu",
    "Use it on the rock in the western opening":
        "Utilisez-le sur le rocher dans l'ouverture ouest",
    "Use on the Big Octo to remove the Great Sea Rule":
        "Utilisez sur le Grand Octo pour retirer la Règle Grande Mer",
    "Use on the butterflies":
        "Utilisez sur les papillons",
    "Use on the dock":
        "Utilisez sur le quai",
    "Use on the eastern statue":
        "Utilisez sur la statue est",
    "Use on the easternmost pier":
        "Utilisez sur l'embarcadère le plus à l'est",
    "Use on the giant switch":
        "Utilisez sur l'interrupteur géant",
    "Use on the grapple mark to the left of the waterfall":
        "Utilisez sur la cible du Grappin à gauche de la cascade",
    "Use on the marker northeast of the tower door":
        "Utilisez sur la cible au nord-est de la porte de la tour",
    "Use on the marker west of the large rock in the north":
        "Utilisez sur la cible à l'ouest du grand rocher au nord",
    "Use on the pier":
        "Utilisez sur l'embarcadère",
    "Use on the ring of light":
        "Utilisez sur l'anneau de lumière",
    "Use on the sea spray":
        "Utilisez sur les embruns",
    "Use on the seagull":
        "Utilisez sur la mouette",
    "Use on the soft dirt":
        "Utilisez sur la terre meuble",
    "Use on the stone head":
        "Utilisez sur la tête de pierre",
    "Use on the tornado to remove Great Sea Rule":
        "Utilisez sur la tornade pour retirer la Règle Grande Mer",
    "Use on the warship to remove Great Sea Rule":
        "Utilisez sur le navire de guerre pour retirer la Règle Grande Mer",
    "Use on the windmill":
        "Utilisez sur le moulin",
    "Use to clear the headwinds":
        "Utilisez pour dégager les vents contraires",
    # ── LORULE — cartes-objets et actions (ajoutées v2 — map Lorule) ────────────
    "Use on the tile":
        "Utilisez sur la tuile",
    "Use on the wooden post":
        "Utilisez sur le poteau en bois",
    "Use on the cracked wall":
        "Utilisez sur le mur fissuré",
    "Use on the rock":
        "Utilisez sur le rocher",
    "Use on the ice statue":
        "Utilisez sur la statue de glace",
    "Use on the flame statue":
        "Utilisez sur la statue de feu",
    "Use on the sand mound":
        "Utilisez sur le monticule de sable",
    "Use on the switch":
        "Utilisez sur l'interrupteur",
    "Use on the target":
        "Utilisez sur la cible",
    "Give to the Mother Maiamai":
        "Donnez à la Mère Maïamaï",
    "Shoot the Beamos":
        "Tirez sur le Beamos",
}


def extract_descriptions(html_path):
    """Extrait toutes les descriptions EN du GUIDE pour les soumettre à traduction."""
    with open(html_path) as f:
        content = f.read()
    idx = content.find('const GUIDE=')
    guide = json.loads(content[idx+12:content.find('\nconst ', idx+12)].rstrip().rstrip(';'))
    descs = set()
    for mn, cells in guide.items():
        for coord, cell in cells.items():
            for f in ['skull_1','skull_2']:
                v = cell.get(f)
                if v and isinstance(v, str): descs.add(v)
            for item in cell.get('search',[]):
                if item.get('desc'): descs.add(item['desc'])
    return sorted(descs)


def apply_translations(html_path, translations=None):
    """Applique le dict de traductions directement dans le GUIDE du HTML."""
    if translations is None:
        translations = TRANSLATIONS
    with open(html_path) as f:
        content = f.read()

    idx = content.find('const GUIDE=')
    start = idx + 12
    end = content.find('\nconst ', start)
    guide = json.loads(content[start:end].rstrip().rstrip(';'))

    changed = 0
    for mn, cells in guide.items():
        for coord, cell in cells.items():
            for field in ['skull_1','skull_2']:
                v = cell.get(field)
                if v and v in translations:
                    cell[field] = translations[v]
                    changed += 1
            for item in cell.get('search', []):
                d = item.get('desc','')
                if d and d in translations:
                    item['desc'] = translations[d]
                    changed += 1

    new_guide = 'const GUIDE=' + json.dumps(guide, ensure_ascii=False, separators=(',',':')) + ';'
    old_guide = 'const GUIDE=' + content[start:end].rstrip().rstrip(';') + ';'
    new_content = content.replace(old_guide, new_guide)
    print(f"  {changed} descriptions traduites dans {len(guide)} maps", file=sys.stderr)
    return new_content


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Traduit les descriptions du GUIDE HWDE')
    parser.add_argument('html', help='Fichier HTML tracker')
    parser.add_argument('--extract', action='store_true',
                        help='Extraire les descriptions EN (pour les soumettre à traduction)')
    parser.add_argument('--apply', action='store_true',
                        help='Appliquer les traductions dans le fichier HTML')
    parser.add_argument('--out', default=None,
                        help='Fichier de sortie (défaut: modifie en place)')
    args = parser.parse_args()

    if args.extract:
        descs = extract_descriptions(args.html)
        print(json.dumps(descs, ensure_ascii=False, indent=2))
    elif args.apply:
        new_content = apply_translations(args.html)
        out = args.out or args.html
        with open(out, 'w') as f:
            f.write(new_content)
        print(f"Écrit dans {out}", file=sys.stderr)
    else:
        parser.print_help()
