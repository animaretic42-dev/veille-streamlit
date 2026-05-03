"""
visuel.py — Génération de visuels JPG avec charte graphique dynamique
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import os
import re
from io import BytesIO
from datetime import datetime


# ─────────────────────────────────────────
# POLICES
# ─────────────────────────────────────────
def trouver_police(taille, gras=False):
    # Cherche d'abord dans le dossier local (veille-pro/)
    # puis dans les polices Windows
    # DejaVuSans est prioritaire car il supporte tous les accents français
    dossier_local = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    candidats_gras = [
        os.path.join(dossier_local, "DejaVuSans.ttf"),
        "DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "Montserrat-Bold.ttf",
    ]
    candidats_normal = [
        os.path.join(dossier_local, "DejaVuSans.ttf"),
        "DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "Montserrat-Regular.ttf",
    ]
    for nom in (candidats_gras if gras else candidats_normal):
        try:
            return ImageFont.truetype(nom, taille)
        except:
            continue
    return ImageFont.load_default()

# ─────────────────────────────────────────
# NETTOYAGE HTML
# ─────────────────────────────────────────
def nettoyer_html(texte):
    if not texte:
        return ""
    texte = re.sub(r'<figure>.*?</figure>', '', texte, flags=re.DOTALL)
    texte = re.sub(r'<[^>]+>', ' ', texte)
    remplacements = {
        '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
        '&rsquo;': "'", '&lsquo;': "'", '&ldquo;': '"', '&rdquo;': '"',
        '&laquo;': chr(171), '&raquo;': chr(187),
        '&eacute;': chr(233), '&egrave;': chr(232), '&ecirc;': chr(234),
        '&agrave;': chr(224), '&ugrave;': chr(249), '&ccedil;': chr(231),
        '&ocirc;':  chr(244), '&ucirc;':  chr(251), '&iuml;':  chr(239),
        '&euml;':   chr(235), '&acirc;':  chr(226), '&icirc;': chr(238),
        '&oelig;':  chr(339), '&Eacute;': chr(201),
        '&#8217;': "'", '&#8216;': "'", '&#8220;': '"', '&#8221;': '"',
        '&#8230;': '...', '&#160;': ' ', '\u00a0': ' ',
    }
    for k, v in remplacements.items():
        texte = texte.replace(k, v)
    return ' '.join(texte.split()).strip()


# ─────────────────────────────────────────
# IMAGE UNSPLASH — CROP CENTRÉ
# ─────────────────────────────────────────
def telecharger_image(image_url, w, h):
    try:
        r   = requests.get(image_url, timeout=15)
        img = Image.open(BytesIO(r.content)).convert("RGB")
        ratio_c = w / h
        ratio_i = img.width / img.height
        if ratio_i > ratio_c:
            nh = h
            nw = int(nh * ratio_i)
        else:
            nw = w
            nh = int(nw / ratio_i)
        img  = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - w) // 2
        top  = (nh - h) // 2
        return img.crop((left, top, left + w, top + h))
    except Exception as e:
        print(f"Image erreur : {e}")
        return Image.new("RGB", (w, h), (200, 210, 220))


# ─────────────────────────────────────────
# DÉGRADÉ
# ─────────────────────────────────────────
def degrade(draw, x1, y1, x2, y2, c1, c2, vertical=True):
    n = (y2 - y1) if vertical else (x2 - x1)
    for i in range(n):
        t = i / max(n, 1)
        c = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
        if vertical:
            draw.line([(x1, y1+i), (x2, y1+i)], fill=c)
        else:
            draw.line([(x1+i, y1), (x1+i, y2)], fill=c)


# ─────────────────────────────────────────
# BLOB DÉCORATIF
# ─────────────────────────────────────────
def blob(img, cx, cy, rx, ry, couleur, alpha=70):
    b = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(b).ellipse(
        [cx-rx, cy-ry, cx+rx, cy+ry],
        fill=(couleur[0], couleur[1], couleur[2], alpha)
    )
    b = b.filter(ImageFilter.GaussianBlur(radius=55))
    return Image.alpha_composite(img.convert("RGBA"), b).convert("RGB")


# ─────────────────────────────────────────
# TEXTE JUSTIFIÉ
# ─────────────────────────────────────────
def texte_justifie(draw, texte, x, y, larg, police, couleur, interligne):
    mots  = texte.split()
    lignes = []
    ligne  = []
    for mot in mots:
        test = ' '.join(ligne + [mot])
        if draw.textbbox((0, 0), test, font=police)[2] <= larg:
            ligne.append(mot)
        else:
            if ligne:
                lignes.append(ligne)
            ligne = [mot]
    if ligne:
        lignes.append(ligne)

    y_c = y
    for i, l in enumerate(lignes):
        derniere = (i == len(lignes) - 1)
        if len(l) <= 1 or derniere:
            draw.text((x, y_c), ' '.join(l), font=police, fill=couleur)
        else:
            larg_mots = sum(draw.textbbox((0, 0), m, font=police)[2] for m in l)
            esp = (larg - larg_mots) / max(len(l) - 1, 1)
            xm  = x
            for mot in l:
                draw.text((int(xm), y_c), mot, font=police, fill=couleur)
                xm += draw.textbbox((0, 0), mot, font=police)[2] + esp
        y_c += interligne
    return y_c


# ─────────────────────────────────────────
# TITRE SUR 2 LIGNES MAX — ADAPTATIF
# ─────────────────────────────────────────
def titre_deux_lignes(draw, titre, x, y, larg_max, couleur):
    """
    Affiche le titre sur 1 ou 2 lignes maximum.
    Réduit la taille de police pour faire tenir sur 2 lignes.
    Ne coupe plus jamais avec des points de suspension.
    """
    for taille in range(72, 22, -2):
        police = trouver_police(taille, gras=True)
        bbox   = draw.textbbox((0, 0), titre, font=police)
        larg_titre = bbox[2] - bbox[0]

        # Cas 1 — Le titre tient sur une seule ligne
        if larg_titre <= larg_max:
            draw.text((x, y), titre, font=police, fill=couleur)
            h_ligne = bbox[3] - bbox[1]
            return y + h_ligne + 14, taille

        # Cas 2 — Essayer de couper en 2 lignes
        mots  = titre.split()
        meilleure_coupure = None
        for i in range(1, len(mots)):
            ligne1 = ' '.join(mots[:i])
            ligne2 = ' '.join(mots[i:])
            b1 = draw.textbbox((0, 0), ligne1, font=police)
            b2 = draw.textbbox((0, 0), ligne2, font=police)
            if b1[2] <= larg_max and b2[2] <= larg_max:
                # Les deux lignes tiennent — cherche la coupure la plus équilibrée
                diff = abs((b1[2] - b1[0]) - (b2[2] - b2[0]))
                if meilleure_coupure is None or diff < meilleure_coupure[0]:
                    meilleure_coupure = (diff, ligne1, ligne2, b1, b2)

        if meilleure_coupure:
            _, ligne1, ligne2, b1, b2 = meilleure_coupure
            h_ligne = b1[3] - b1[1]
            draw.text((x, y),              ligne1, font=police, fill=couleur)
            draw.text((x, y + h_ligne + 6), ligne2, font=police, fill=couleur)
            return y + h_ligne * 2 + 20, taille

    # Dernier recours taille 22 — coupe forcée équilibrée
    police = trouver_police(22, gras=True)
    mots   = titre.split()
    milieu = len(mots) // 2
    ligne1 = ' '.join(mots[:milieu])
    ligne2 = ' '.join(mots[milieu:])
    b1     = draw.textbbox((0, 0), ligne1, font=police)
    h      = b1[3] - b1[1]
    draw.text((x, y),         ligne1, font=police, fill=couleur)
    draw.text((x, y + h + 6), ligne2, font=police, fill=couleur)
    return y + h * 2 + 20, 22


# ─────────────────────────────────────────
# TAILLE POLICE ADAPTATIVE CORRIGÉE
# Basée sur la zone disponible réelle
# ─────────────────────────────────────────
def taille_adaptative_zone(nb_chars, largeur_zone, hauteur_zone):
    """
    Calcule la taille de police optimale pour remplir
    au mieux la zone de texte disponible.
    """
    for taille in range(32, 11, -1):
        interligne   = int(taille * 1.6)
        chars_ligne  = int(largeur_zone / (taille * 0.50))
        nb_lignes    = int(hauteur_zone / interligne)
        capacite     = int(nb_lignes * chars_ligne * 0.90)
        if nb_chars <= capacite:
            return taille
    return 13


# ─────────────────────────────────────────
# GÉNÉRATION DU VISUEL
# ─────────────────────────────────────────
def generer_visuel(article, nom_fichier, charte, logo_path=None):
    from core.charte import charte_defaut
    if charte is None:
        charte = charte_defaut()

    C = charte["couleurs"]
    S = charte["structure"]

    LARGEUR = 1400
    HAUTEUR = 990
    dossier_sortie = "output/articles_ok" # Définition de la variable manquante

    genere       = article["genere"]
    source       = article["source"]
    contenu_html = genere.get("contenu", "")
    titre        = nettoyer_html(genere.get("titre", ""))
    contenu      = nettoyer_html(contenu_html)
    tags         = genere.get("tags", [])
    image_url    = genere.get("image_url")
    image_credit = nettoyer_html(genere.get("image_credit", ""))
    lien_source  = source.get("lien", "")
    nom_source   = nettoyer_html(source.get("source", ""))
    date_str     = datetime.now().strftime("%d/%m/%Y")

    pol_date  = trouver_police(26, gras=True)
    pol_bold  = trouver_police(20, gras=True)
    pol_small = trouver_police(13, gras=False)

    # ── Canvas + blobs ────────────────────
    img = Image.new("RGB", (LARGEUR, HAUTEUR), C.get("fond", (255, 255, 255)))
    c_blob1 = C.get("tag3",       (240, 180, 120))
    c_blob2 = C.get("tag2",       (180, 140, 220))
    c_blob3 = C.get("principale", (140, 200, 240))
    img = blob(img, LARGEUR-200, HAUTEUR-150, 350, 280, c_blob1, 65)
    img = blob(img, 150,         HAUTEUR-100, 300, 250, c_blob2, 55)
    img = blob(img, LARGEUR//2,  HAUTEUR-50,  400, 200, c_blob3, 40)
    draw = ImageDraw.Draw(img)

    # ── HEADER ────────────────────────────
    header_h = S.get("hauteur_header", 100)
    c_h1 = C.get("header",     (180, 160, 220))
    c_h2 = C.get("principale", (140, 200, 240))
    degrade(draw, 0, 0, LARGEUR, header_h, c_h1, c_h2, vertical=False)

    date_texte = f"Veille du {date_str}"
    bbox_d     = draw.textbbox((0, 0), date_texte, font=pol_date)
    draw.text(
        (LARGEUR - (bbox_d[2]-bbox_d[0]) - 30,
         (header_h - (bbox_d[3]-bbox_d[1])) // 2),
        date_texte, font=pol_date, fill=(255, 255, 255)
    )

    # ── LOGO ──────────────────────────────
    logo_cx, logo_cy, logo_r = 110, header_h + 82, 70
    draw.ellipse(
        [logo_cx-logo_r, logo_cy-logo_r, logo_cx+logo_r, logo_cy+logo_r],
        fill=C.get("secondaire", (220, 200, 240))
    )
    logo_ok = False
    
    # Priorité au logo personnel de l'utilisateur
    if logo_path and os.path.exists(logo_path):
        try:
            li = Image.open(logo_path).convert("RGBA")
            tl = int(logo_r * 1.5)
            li = li.resize((tl, tl), Image.LANCZOS)
            img.paste(li, (logo_cx - tl//2, logo_cy - tl//2), li)
            logo_ok = True
        except:
            pass

    # Sinon, vérification des fichiers locaux par défaut
    if not logo_ok:
        for nom_logo in ["logo.png", "logo.jpg", "logo.jpeg"]:
            if os.path.exists(nom_logo):
                try:
                    li = Image.open(nom_logo).convert("RGBA")
                    tl = int(logo_r * 1.5)
                    li = li.resize((tl, tl), Image.LANCZOS)
                    img.paste(li, (logo_cx - tl//2, logo_cy - tl//2), li)
                    logo_ok = True
                    break
                except:
                    pass
                    
    if not logo_ok:
        draw.text((logo_cx-18, logo_cy-12), "VN",
                  font=pol_bold, fill=C.get("principale", (60, 100, 180)))

    # ── TITRE SUR 2 LIGNES MAX ────────────
    titre_x = logo_cx + logo_r + 25
    titre_w = LARGEUR - titre_x - 40
    y_st, taille_titre = titre_deux_lignes(
        draw, titre, titre_x, header_h + 15, titre_w,
        C.get("texte", (30, 30, 30))
    )

    # ── SOURCE ────────────────────────────
    c_source = C.get("principale", (60, 100, 180))
    src_lbl  = f"Source : {nom_source}"
    draw.text((titre_x, y_st), src_lbl, font=pol_bold, fill=c_source)
    bbox_src = draw.textbbox((titre_x, y_st), src_lbl, font=pol_bold)
    draw.line(
        [(bbox_src[0], bbox_src[3]+1), (bbox_src[2], bbox_src[3]+1)],
        fill=c_source, width=1
    )

    # ── SÉPARATEUR ────────────────────────
    sep_y = max(y_st + 32, logo_cy + logo_r + 12)
    draw.rectangle(
        [40, sep_y, LARGEUR-40, sep_y+2],
        fill=C.get("secondaire", (200, 200, 200))
    )

    # ── ZONE IMAGE (gauche) ───────────────
    img_x = 40
    img_y = sep_y + 16
    img_w = 468
    img_h = HAUTEUR - img_y - 85

    if image_url:
        photo = telecharger_image(image_url, img_w, img_h)
        mask  = Image.new("L", (img_w, img_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, img_w, img_h], radius=14, fill=255
        )
        img.paste(photo, (img_x, img_y), mask)
    else:
        draw.rounded_rectangle(
            [img_x, img_y, img_x+img_w, img_y+img_h],
            radius=14, fill=(210, 220, 230)
        )

    # Crédit photo UNIQUEMENT sous la photo
    if image_credit:
        draw.text(
            (img_x, img_y + img_h + 3),
            image_credit[:65],
            font=pol_small, fill=(150, 150, 150)
        )

    # ── ZONE TEXTE (droite) ───────────────
    txt_x = img_x + img_w + 28
    txt_y = img_y
    txt_w = LARGEUR - txt_x - 32
    txt_h = img_h - 42

    t_pol      = taille_adaptative_zone(len(contenu), txt_w, txt_h)
    pol_texte  = trouver_police(t_pol, gras=False)
    interligne = int(t_pol * 1.6)

    nb_lignes   = int(txt_h / interligne)
    chars_ligne = int(txt_w / (t_pol * 0.50))
    nb_chars    = int(nb_lignes * chars_ligne * 0.90)

    if len(contenu) > nb_chars:
        affiche = contenu[:nb_chars].rsplit(' ', 1)[0] + "..."
    else:
        affiche = contenu

    texte_justifie(
        draw, affiche, txt_x, txt_y, txt_w,
        pol_texte, C.get("texte", (50, 50, 50)), interligne
    )

    # ── TAGS ──────────────────────────────
    tags_y      = img_y + img_h - 30
    cols_tags   = [
        C.get("tag1", (100, 180, 220)),
        C.get("tag2", (160, 120, 200)),
        C.get("tag3", (230, 160,  80))
    ]
    x_tag = txt_x
    for i, tag in enumerate(tags[:5]):
        tt    = f"  {tag}  "
        col_t = cols_tags[i % len(cols_tags)]
        bbt   = draw.textbbox((0, 0), tt, font=pol_small)
        tw    = bbt[2] - bbt[0] + 10
        if x_tag + tw > LARGEUR - 32:
            break
        draw.rounded_rectangle(
            [x_tag, tags_y, x_tag+tw, tags_y+26],
            radius=13, fill=col_t
        )
        draw.text((x_tag+5, tags_y+5), tt.strip(),
                  font=pol_small, fill=(255, 255, 255))
        x_tag += tw + 8

    # ── FOOTER ────────────────────────────
    fy = HAUTEUR - 66
    draw.rectangle([0, fy, LARGEUR, HAUTEUR],
                   fill=C.get("footer", (80, 160, 200)))
    draw.text((30, fy+18),
              f"Lien : {lien_source[:100]}",
              font=pol_small, fill=(220, 240, 255))

    # ── SAUVEGARDE ────────────────────────
    os.makedirs(dossier_sortie, exist_ok=True)
    chemin = f"{dossier_sortie}/{nom_fichier}.jpg"
    img.save(chemin, "JPEG", quality=95)
    print(f"Visuel sauvegarde : {chemin}")
    return chemin
