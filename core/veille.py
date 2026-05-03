"""
veille.py — Récupération RSS, filtrage et génération d'articles via Claude
"""

import feedparser
import anthropic
import requests
import os
import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ─────────────────────────────────────────
# MOTS-CLÉS DE PERTINENCE
# ─────────────────────────────────────────
MOTS_CLES = [
    "intelligence artificielle", "ia", "ai", "machine learning",
    "cybersécurité", "cyber", "hacking", "phishing", "ransomware",
    "médiation numérique", "numérique", "digital",
    "audiovisuel", "vidéo", "streaming", "podcast",
    "mao", "musique assistée", "daw", "ableton", "logic pro",
    "bonnes pratiques", "sensibilisation", "protection", "données",
    "vie privée", "rgpd", "open source", "linux", "code", "programmation",
    "réseaux sociaux", "internet", "smartphone", "application", "logiciel",
]

# ─────────────────────────────────────────
# HISTORIQUE (anti-doublons)
# ─────────────────────────────────────────
CHEMIN_HISTORIQUE = "data/historique.json"

def charger_historique():
    if os.path.exists(CHEMIN_HISTORIQUE):
        with open(CHEMIN_HISTORIQUE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_historique(ids):
    os.makedirs("data", exist_ok=True)
    with open(CHEMIN_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────
# FILTRAGE PAR MOTS-CLÉS
# ─────────────────────────────────────────
def est_pertinent(titre, resume, mots_cles_custom=None):
    texte = (titre + " " + resume).lower()
    mots  = mots_cles_custom if mots_cles_custom else MOTS_CLES
    return any(mot in texte for mot in mots)

# ─────────────────────────────────────────
# RÉCUPÉRATION DES ARTICLES RSS
# ─────────────────────────────────────────
def recuperer_articles(sources, jours_max=7, mots_cles_custom=None):
    """
    sources       : liste d'URLs de flux RSS
    jours_max     : ne garder que les articles des N derniers jours
    mots_cles_custom : liste de mots-clés personnalisés (optionnel)
    """
    articles    = []
    historique  = charger_historique()
    logs        = []

    for url in sources:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        log = {"url": url, "nb": 0, "erreur": None}
        try:
            feed     = feedparser.parse(url)
            nom_src  = feed.feed.get("title", url)
            nouveaux = 0

            for entry in feed.entries[:15]:
                id_article = hashlib.md5(entry.get("link","").encode()).hexdigest()
                if id_article in historique:
                    continue

                titre  = entry.get("title", "Sans titre")
                resume = entry.get("summary", "")[:1500]

                # Filtre date
                date_publi = entry.get("published_parsed") or entry.get("updated_parsed")
                if date_publi:
                    date_article = datetime(*date_publi[:6], tzinfo=timezone.utc)
                    date_limite  = datetime.now(timezone.utc) - timedelta(days=jours_max)
                    if date_article < date_limite:
                        continue

                # Filtre pertinence
                if not est_pertinent(titre, resume, mots_cles_custom):
                    continue

                articles.append({
                    "id":          id_article,
                    "titre":       titre,
                    "lien":        entry.get("link", ""),
                    "resume":      resume,
                    "source":      nom_src,
                    "date_source": entry.get("published", "Date inconnue"),
                })
                nouveaux += 1

            log["nb"]  = nouveaux
            log["nom"] = nom_src
        except Exception as e:
            log["erreur"] = str(e)
        logs.append(log)

    return articles, logs


# ─────────────────────────────────────────
# RECHERCHE D'IMAGE UNSPLASH
# ─────────────────────────────────────────
def chercher_image(mot_cle_image):
    unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not unsplash_key:
        return None, None
    try:
        response = requests.get(
            "https://api.unsplash.com/photos/random",
            params={"query": mot_cle_image, "orientation": "landscape", "content_filter": "high"},
            headers={"Authorization": f"Client-ID {unsplash_key}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data["urls"]["regular"], f"Photo by {data['user']['name']} on Unsplash"
    except Exception as e:
        print(f"Unsplash erreur : {e}")
    return None, None


# ─────────────────────────────────────────
# GÉNÉRATION D'ARTICLE AVEC CLAUDE
# ─────────────────────────────────────────
def generer_article(article_source, style_redaction="médiation numérique"):
    prompt = f"""
Tu es rédacteur web spécialisé en {style_redaction} pour un site français.
Ton public est composé de professionnels, d'éducateurs et de particuliers.

À partir de cet article source :
- Titre original : {article_source['titre']}
- Source : {article_source['source']}
- Résumé : {article_source['resume']}
- Lien original : {article_source['lien']}

Génère un article de veille en français avec :
1. Un titre accrocheur (différent de l'original)
2. Une introduction claire de 2-3 phrases
3. Deux ou trois paragraphes de développement accessibles
4. Une conclusion avec l'enjeu concret pour les usagers
5. Mention de la source originale à la fin

Réponds UNIQUEMENT avec un objet JSON valide contenant :
- "titre" : titre de l'article
- "contenu" : corps en HTML simple (<p>, <strong>, <h3>)
- "extrait" : une phrase résumé (max 160 caractères)
- "tags" : liste de 3 à 5 mots-clés en français
- "image_keyword" : UN mot-clé en ANGLAIS précis et visuel pour illustrer l'article
"""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    texte = message.content[0].text.strip()
    if "```json" in texte:
        texte = texte.split("```json")[1].split("```")[0].strip()
    elif "```" in texte:
        texte = texte.split("```")[1].split("```")[0].strip()
    return json.loads(texte)


# ─────────────────────────────────────────
# PIPELINE COMPLET
# ─────────────────────────────────────────
def lancer_veille(sources, jours_max=7, mots_cles_custom=None,
                  style_redaction="médiation numérique", callback=None):
    """
    Lance la veille complète.
    callback(message) : fonction appelée pour afficher la progression (optionnel)
    Retourne : (nb_generes, nb_erreurs, logs_sources)
    """
    def log(msg):
        if callback:
            callback(msg)
        else:
            print(msg)

    articles, logs_sources = recuperer_articles(sources, jours_max, mots_cles_custom)
    log(f"📰 {len(articles)} article(s) trouvé(s)")

    if not articles:
        return 0, 0, logs_sources

    historique     = charger_historique()
    nb_generes     = 0
    nb_erreurs     = 0

    for i, article in enumerate(articles, 1):
        log(f"[{i}/{len(articles)}] Génération : {article['titre'][:55]}...")
        try:
            genere = generer_article(article, style_redaction)

            # Chercher une image
            mot_cle      = genere.get("image_keyword", "digital technology")
            image_url, image_credit = chercher_image(mot_cle)

            if image_url:
                genere["image_url"]    = image_url
                genere["image_credit"] = image_credit
                # Injecter l'image dans le contenu HTML
                img_html = (
                    f'<figure>'
                    f'<img src="{image_url}" alt="{genere["titre"]}" '
                    f'style="width:100%;border-radius:8px;">'
                    f'<figcaption style="font-size:0.8em;color:#666;">{image_credit}</figcaption>'
                    f'</figure>\n\n'
                )
                genere["contenu"] = img_html + genere["contenu"]
                log(f"   Image trouvée : {mot_cle}")

            # Sauvegarder
            os.makedirs("data/articles", exist_ok=True)
            chemin = f"data/articles/{article['id']}.json"
            data   = {
                "source":           article,
                "genere":           genere,
                "date_generation":  datetime.now().isoformat(),
                "statut":           "en_attente",
            }
            with open(chemin, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            historique.append(article["id"])
            nb_generes += 1
            log(f"   Sauvegardé : {genere['titre']}")

        except json.JSONDecodeError:
            log(f"   Erreur JSON sur : {article['titre']}")
            nb_erreurs += 1
        except Exception as e:
            log(f"   Erreur : {e}")
            nb_erreurs += 1

    sauvegarder_historique(historique)
    return nb_generes, nb_erreurs, logs_sources


# ─────────────────────────────────────────
# CHARGER LES ARTICLES
# ─────────────────────────────────────────
def charger_articles(statut="tous"):
    import glob
    fichiers = glob.glob("data/articles/*.json")
    articles = []
    for f in fichiers:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                data["_fichier"] = f
                if statut == "tous" or data.get("statut") == statut:
                    articles.append(data)
        except:
            pass
    articles.sort(key=lambda x: x.get("date_generation", ""), reverse=True)
    return articles

def sauvegarder_statut(fichier, nouveau_statut):
    with open(fichier, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["statut"]      = nouveau_statut
    data["date_action"] = datetime.now().isoformat()
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
