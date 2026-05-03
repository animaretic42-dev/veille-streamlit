from PIL import Image
import numpy as np
from colorthief import ColorThief
import io
import json
import os


def extraire_couleurs(image_pil, nb_couleurs=6):
    buffer = io.BytesIO()
    image_pil.save(buffer, format="PNG")
    buffer.seek(0)
    try:
        ct = ColorThief(buffer)
        palette = ct.get_palette(color_count=nb_couleurs, quality=1)
    except Exception:
        img_array = np.array(image_pil.convert("RGB").resize((150, 150)))
        pixels = img_array.reshape(-1, 3)
        palette = [tuple(p) for p in pixels[::len(pixels)//nb_couleurs][:nb_couleurs]]
    return palette


def classer_couleurs(palette):
    def luminosite(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    def saturation(c):
        r, g, b = c[0]/255, c[1]/255, c[2]/255
        mx, mn = max(r, g, b), min(r, g, b)
        return (mx - mn) / mx if mx != 0 else 0

    triees_lum = sorted(palette, key=luminosite, reverse=True)
    triees_sat = sorted(palette, key=saturation, reverse=True)

    return {
        "fond":       triees_lum[0],
        "secondaire": triees_lum[1] if len(triees_lum) > 1 else triees_lum[0],
        "principale": triees_sat[0],
        "accent":     triees_sat[1] if len(triees_sat) > 1 else triees_sat[0],
        "texte":      triees_lum[-1],
        "header":     triees_sat[0],
        "footer":     triees_lum[-2] if len(triees_lum) > 2 else triees_lum[-1],
        "tag1":       triees_sat[0],
        "tag2":       triees_sat[1] if len(triees_sat) > 1 else triees_sat[0],
        "tag3":       triees_sat[2] if len(triees_sat) > 2 else triees_sat[0],
    }


def analyser_structure(image_pil):
    w, h = image_pil.size
    img_array = np.array(image_pil.convert("RGB"))
    hauteur_header = 80
    for y in range(10, min(200, h)):
        diff = np.mean(np.abs(
            img_array[y, :, :].astype(int) - img_array[0, :, :].astype(int)
        ))
        if diff > 40:
            hauteur_header = y
            break
    var_gauche = float(np.var(img_array[:, :w//2, :]))
    var_droite = float(np.var(img_array[:, w//2:, :]))
    return {
        "largeur":        int(w),
        "hauteur":        int(h),
        "format_paysage": bool(w > h),
        "hauteur_header": int(hauteur_header),
        "image_a_gauche": bool(var_gauche > var_droite),
        "ratio":          round(w / h, 2),
    }


def analyser_charte(image_pil):
    palette   = extraire_couleurs(image_pil, nb_couleurs=8)
    couleurs  = classer_couleurs(palette)
    structure = analyser_structure(image_pil)
    return {
        "couleurs":  couleurs,
        "structure": structure,
        "palette":   palette,
    }


def sauvegarder_charte(charte, chemin="data/charte.json"):
    def convertir(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, bool):
            return bool(obj)
        if isinstance(obj, tuple):
            return [convertir(i) for i in obj]
        if isinstance(obj, list):
            return [convertir(i) for i in obj]
        if isinstance(obj, dict):
            return {k: convertir(v) for k, v in obj.items()}
        return obj

    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    charte_propre = convertir(charte)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(charte_propre, f, ensure_ascii=False, indent=2)


def charger_charte(chemin="data/charte.json"):
    if not os.path.exists(chemin):
        return None
    with open(chemin, "r", encoding="utf-8") as f:
        charte = json.load(f)

    def to_tuple(val):
        if isinstance(val, list) and len(val) == 3:
            return tuple(val)
        return val

    if "couleurs" in charte:
        charte["couleurs"] = {k: to_tuple(v) for k, v in charte["couleurs"].items()}
    if "palette" in charte:
        charte["palette"] = [to_tuple(c) for c in charte["palette"]]
    return charte


def charte_defaut():
    return {
        "couleurs": {
            "fond":       (255, 255, 255),
            "secondaire": (245, 245, 245),
            "principale": (30,  87,  153),
            "accent":     (231, 76,   60),
            "texte":      (40,  40,   40),
            "header":     (30,  87,  153),
            "footer":     (50,  50,   50),
            "tag1":       (100, 180, 220),
            "tag2":       (160, 120, 200),
            "tag3":       (230, 160,  80),
        },
        "structure": {
            "largeur":        1400,
            "hauteur":         990,
            "format_paysage":  True,
            "hauteur_header":  100,
            "image_a_gauche":  True,
            "ratio":           1.41,
        },
        "palette": [
            (30, 87, 153), (231, 76, 60), (255, 255, 255),
            (40, 40, 40),  (100, 180, 220), (160, 120, 200)
        ]
    }
