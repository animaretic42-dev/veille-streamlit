"""
app.py — Application de veille numérique professionnelle
Streamlit multi-pages avec gestion RSS, validation et génération visuelle
"""

import streamlit as st
import json
import os
import glob
from datetime import datetime
from PIL import Image
import io

# ─────────────────────────────────────────
# GESTION DES SECRETS STREAMLIT
# ─────────────────────────────────────────
if "ANTHROPIC_API_KEY" in st.secrets:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
if "UNSPLASH_ACCESS_KEY" in st.secrets:
    os.environ["UNSPLASH_ACCESS_KEY"] = st.secrets["UNSPLASH_ACCESS_KEY"]
    
# Import des modules core
from core.veille  import lancer_veille, charger_articles, sauvegarder_statut
from core.charte  import analyser_charte, sauvegarder_charte, charger_charte, charte_defaut
from core.visuel  import generer_visuel

# ─────────────────────────────────────────
# CONFIGURATION PAGE
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Veille Numérique Pro",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔴 RÉINITIALISATION AUTOMATIQUE À L'OUVERTURE
if "init_effectue" not in st.session_state:
    import shutil
    import os
    
    dossiers_a_vider = ["data", "output/articles_ok"]
    for dossier in dossiers_a_vider:
        if os.path.exists(dossier):
            shutil.rmtree(dossier)
            
    st.session_state["init_effectue"] = True # Pour ne le faire qu'une seule fois par session
# ─────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a5f 0%, #2d6a9f 100%); }
    [data-testid="stSidebar"] * { color: white !important; }

    /* Métriques */
    [data-testid="metric-container"] {
        background: #f0f4f8; border-radius: 10px;
        padding: 12px; border-left: 4px solid #2d6a9f;
    }

    /* Badges statut */
    .badge-attente { background:#fff3cd; color:#856404; padding:3px 10px; border-radius:10px; font-size:0.82em; }
    .badge-publie  { background:#d4edda; color:#155724; padding:3px 10px; border-radius:10px; font-size:0.82em; }
    .badge-rejete  { background:#f8d7da; color:#721c24; padding:3px 10px; border-radius:10px; font-size:0.82em; }

    /* Cards articles */
    .article-card {
        border: 1px solid #e0e0e0; border-radius: 10px;
        padding: 16px; margin-bottom: 12px;
        border-left: 5px solid #2d6a9f;
    }

    /* Bouton primaire */
    .stButton > button[kind="primary"] { background: #2d6a9f; border: none; }

    /* Titres sections */
    h2 { color: #1e3a5f; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# CHARGEMENT CONFIG
# ─────────────────────────────────────────
def charger_config():
    if os.path.exists("data/config.json"):
        with open("data/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "sources":         [],
        "jours_max":       7,
        "style_redaction": "médiation numérique",
        "mots_cles":       [],
        "nom_site":        "Veille Numérique",
    }

def sauvegarder_config(config):
    os.makedirs("data", exist_ok=True)
    with open("data/config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# SIDEBAR — NAVIGATION
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📡 Veille Numérique Pro")
    st.markdown("---")

    # 🔴 Réinitialisation des données
    if st.sidebar.button("🗑️ Réinitialiser l'application", type="secondary", use_container_width=True):
        import shutil
        
        # Suppression des dossiers de données et articles
        dossiers_a_vider = ["data", "output/articles_ok"]
        for dossier in dossiers_a_vider:
            if os.path.exists(dossier):
                shutil.rmtree(dossier)
                
        st.sidebar.success("Données réinitialisées à zéro !")
        st.rerun()
        
    page = st.radio(
        "Navigation",
        ["🏠 Tableau de bord", "📋 Sources RSS", "📰 Articles", "🎨 Charte graphique"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Compteurs rapides
    articles_attente = charger_articles("en_attente")
    articles_publie  = charger_articles("publié")
    st.metric("⏳ En attente", len(articles_attente))
    st.metric("✅ Publiés",    len(articles_publie))

    st.markdown("---")
    st.markdown("<small>Propulsé par Claude (Anthropic)</small>", unsafe_allow_html=True)


# ─────────────────────────────────────────
# PAGE 1 — TABLEAU DE BORD
# ─────────────────────────────────────────
if page == "🏠 Tableau de bord":
    config = charger_config()

    st.title("🏠 Tableau de bord")
    st.markdown(f"Bienvenue sur **{config.get('nom_site','Veille Numérique Pro')}**")
    st.divider()

    # Métriques
    tous     = charger_articles("tous")
    attente  = charger_articles("en_attente")
    publies  = charger_articles("publié")
    rejetes  = charger_articles("rejeté")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total articles",  len(tous))
    c2.metric("⏳ En attente",       len(attente))
    c3.metric("✅ Publiés",          len(publies))
    c4.metric("🗑️ Rejetés",          len(rejetes))

    st.divider()

    # Lancer la veille
    st.subheader("🚀 Lancer une veille")

    if not config.get("sources"):
        st.warning("⚠️ Aucune source RSS configurée. Va dans **Sources RSS** pour en ajouter.")
    else:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            jours = st.slider("Période de veille (jours)", 1, 30,
                              config.get("jours_max", 7))
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            lancer = st.button("▶️ Lancer la veille", type="primary",
                               use_container_width=True)

        if lancer:
            with st.spinner("Veille en cours..."):
                log_zone = st.empty()
                logs_messages = []

                def afficher_log(msg):
                    logs_messages.append(msg)
                    log_zone.text('\n'.join(logs_messages[-15:]))

                nb_gen, nb_err, logs_src = lancer_veille(
                    sources         = config["sources"],
                    jours_max       = jours,
                    mots_cles_custom= config.get("mots_cles") or None,
                    style_redaction = config.get("style_redaction","médiation numérique"),
                    callback        = afficher_log,
                )

            st.success(f"✅ Veille terminée — {nb_gen} articles générés, {nb_err} erreurs")

            # Détail par source
            st.markdown("**Détail par source :**")
            for log in logs_src:
                if log.get("erreur"):
                    st.error(f"❌ {log['url']} — {log['erreur']}")
                else:
                    st.info(f"✅ {log.get('nom', log['url'])} — {log['nb']} article(s)")

    st.divider()

    # Derniers articles
    if tous:
        st.subheader("📰 Derniers articles générés")
        for art in tous[:5]:
            statut = art.get("statut","en_attente")
            badge  = {
                "en_attente": '<span class="badge-attente">⏳ En attente</span>',
                "publié":     '<span class="badge-publie">✅ Publié</span>',
                "rejeté":     '<span class="badge-rejete">🗑️ Rejeté</span>',
            }.get(statut,"")
            st.markdown(
                f'<div class="article-card">'
                f'<b>{art["genere"]["titre"]}</b> &nbsp; {badge}<br>'
                f'<small>Source : {art["source"]["source"]} — '
                f'{art.get("date_generation","")[:10]}</small>'
                f'</div>',
                unsafe_allow_html=True
            )


# ─────────────────────────────────────────
# PAGE 2 — SOURCES RSS
# ─────────────────────────────────────────
elif page == "📋 Sources RSS":
    config = charger_config()
    st.title("📋 Gestion des sources RSS")
    st.divider()

    # Paramètres généraux
    with st.expander("⚙️ Paramètres généraux", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            nom_site = st.text_input("Nom de ton site/service",
                                     value=config.get("nom_site","Veille Numérique"))
            jours_max = st.slider("Ancienneté max des articles (jours)", 1, 60,
                                  config.get("jours_max", 7))
        with col2:
            style = st.text_input("Style de rédaction",
                                  value=config.get("style_redaction","médiation numérique"),
                                  help="Ex: cybersécurité, médiation numérique, IA...")
            mots_cles_str = st.text_area(
                "Mots-clés personnalisés (un par ligne, laisser vide pour utiliser les défauts)",
                value='\n'.join(config.get("mots_cles",[])),
                height=100
            )

    # Gestion des sources
    st.subheader("🔗 Flux RSS")
    st.markdown("Entre entre **3 et 10 flux RSS** (un par ligne) :")

    sources_str = st.text_area(
        "Sources RSS",
        value='\n'.join(config.get("sources",[])),
        height=220,
        help="Une URL de flux RSS par ligne. Les lignes commençant par # sont ignorées.",
        label_visibility="collapsed"
    )

    # Suggestions de sources
    with st.expander("💡 Suggestions de sources RSS par thématique"):
        st.markdown("""
**Cybersécurité**
- `https://www.cybermalveillance.gouv.fr/feed/atom-flux-bonnes-pratiques`
- `https://www.cybermalveillance.gouv.fr/feed/atom-flux-actualites`
- `https://www.ssi.gouv.fr/feed/`

**Intelligence Artificielle**
- `https://korben.info/feed`
- `https://www.lemondeinformatique.fr/flux-rss-1.xml`

**Médiation numérique**
- `https://www.zoomacom.org/feed/rss/`
- `https://www.geekjunior.fr/feed/`

**Numérique général**
- `https://www.numerama.com/feed/`
- `https://www.01net.com/feed/`
        """)

    col_save, col_test = st.columns(2)

    if col_save.button("💾 Sauvegarder la configuration", type="primary",
                       use_container_width=True):
        sources_liste = [s.strip() for s in sources_str.split('\n')
                         if s.strip() and not s.strip().startswith('#')]
        mots_cles_liste = [m.strip() for m in mots_cles_str.split('\n') if m.strip()]

        config.update({
            "sources":          sources_liste,
            "jours_max":        jours_max,
            "style_redaction":  style,
            "mots_cles":        mots_cles_liste,
            "nom_site":         nom_site,
        })
        sauvegarder_config(config)
        st.success(f"✅ Configuration sauvegardée — {len(sources_liste)} source(s)")

    if col_test.button("🧪 Tester les sources", use_container_width=True):
        import feedparser
        sources_test = [s.strip() for s in sources_str.split('\n')
                        if s.strip() and not s.strip().startswith('#')]
        for url in sources_test:
            try:
                feed = feedparser.parse(url)
                nb   = len(feed.entries)
                nom  = feed.feed.get("title", url)
                if nb > 0:
                    st.success(f"✅ {nom} — {nb} entrées trouvées")
                else:
                    st.warning(f"⚠️ {url} — Flux vide ou invalide")
            except Exception as e:
                st.error(f"❌ {url} — Erreur : {e}")


# ─────────────────────────────────────────
# PAGE 3 — ARTICLES
# ─────────────────────────────────────────
elif page == "📰 Articles":
    st.title("📰 Validation des articles")
    st.divider()

    # Filtres
    col_f1, col_f2 = st.columns([2, 3])
    with col_f1:
        filtre = st.selectbox("Afficher :", [
            "en_attente", "tous", "publié", "rejeté"
        ], format_func=lambda x: {
            "tous": "📋 Tous",
            "en_attente": "⏳ En attente",
            "publié": "✅ Publiés",
            "rejeté": "🗑️ Rejetés"
        }[x])
    with col_f2:
        recherche = st.text_input("🔍 Rechercher", "")

    articles = charger_articles(filtre)
    if recherche:
        articles = [a for a in articles
                    if recherche.lower() in a["genere"]["titre"].lower()
                    or recherche.lower() in a["source"]["source"].lower()]

    st.markdown(f"**{len(articles)} article(s) affiché(s)**")
    st.divider()

    for art in articles:
        statut  = art.get("statut","en_attente")
        fichier = art["_fichier"]
        genere  = art["genere"]
        source  = art["source"]

        badge = {
            "en_attente": '<span class="badge-attente">⏳ En attente</span>',
            "publié":     '<span class="badge-publie">✅ Publié</span>',
            "rejeté":     '<span class="badge-rejete">🗑️ Rejeté</span>',
        }.get(statut,"")

        with st.expander(f"📄 {genere['titre']}", expanded=(statut=="en_attente")):
            st.markdown(
                f'<div class="article-card" style="border-left-color:#aaa;">'
                f'📰 <a href="{source["lien"]}" target="_blank">{source["source"]}</a>'
                f' &nbsp;|&nbsp; 🗓️ {art.get("date_generation","")[:10]}'
                f' &nbsp;|&nbsp; {badge}'
                f'</div>',
                unsafe_allow_html=True
            )

            tab1, tab2, tab3 = st.tabs(["👁️ Aperçu", "📝 HTML", "🔗 Source"])

            with tab1:
                st.markdown(f"### {genere['titre']}")
                st.markdown(genere["contenu"], unsafe_allow_html=True)
                if genere.get("tags"):
                    st.markdown("**Tags :** " + " · ".join([f"`{t}`" for t in genere["tags"]]))

            with tab2:
                st.text_area("HTML", value=genere["contenu"], height=200,
                             key=f"html_{fichier}")

            with tab3:
                st.markdown(f"**Titre original :** {source['titre']}")
                st.markdown(f"**Résumé :** {source['resume'][:400]}...")
                st.markdown(f"**Lien :** [{source['lien']}]({source['lien']})")

            st.markdown("")

            if statut == "en_attente":
                col_a, col_b, col_c = st.columns(3)

                # ── PUBLIER avec charte ─────────────
                if col_a.button("🚀 Publier + Visuel", key=f"pub_{fichier}",
                                type="primary"):
                    st.session_state[f"publier_{fichier}"] = True

                # ── BROUILLON ───────────────────────
                if col_b.button("📝 Brouillon", key=f"bro_{fichier}"):
                    sauvegarder_statut(fichier, "publié")
                    st.success("Marqué comme brouillon")
                    st.rerun()

                # ── REJETER ─────────────────────────
                if col_c.button("🗑️ Rejeter", key=f"rej_{fichier}"):
                    sauvegarder_statut(fichier, "rejeté")
                    st.warning("Article rejeté")
                    st.rerun()

                # ── MODAL PUBLICATION ───────────────
                if st.session_state.get(f"publier_{fichier}"):
                    st.markdown("---")
                    st.markdown("### 🎨 Choisir la charte graphique")

                    col_opt1, col_opt2 = st.columns(2)

                    with col_opt1:
                        st.markdown("**Option A — Uploader une image modèle**")
                        upload = st.file_uploader(
                            "Image de charte (jpg/png)",
                            type=["jpg","jpeg","png"],
                            key=f"upload_{fichier}"
                        )
                        if upload:
                            img_pil = Image.open(upload)
                            st.image(img_pil, caption="Charte uploadée", width=300)

                    with col_opt2:
                        st.markdown("**Option B — Charte sauvegardée**")
                        charte_existante = charger_charte()
                        if charte_existante:
                            st.success("✅ Charte existante trouvée")
                            palette = charte_existante.get("palette",[])
                            cols = st.columns(len(palette[:6]))
                            for i, c in enumerate(palette[:6]):
                                hex_c = '#{:02x}{:02x}{:02x}'.format(*[int(x) for x in c])
                                cols[i].markdown(
                                    f'<div style="background:{hex_c};width:40px;'
                                    f'height:40px;border-radius:5px;"></div>'
                                    f'<small>{hex_c}</small>',
                                    unsafe_allow_html=True
                                )
                        else:
                            st.info("Aucune charte sauvegardée — charte par défaut utilisée")

                    utiliser_defaut = st.checkbox("Utiliser la charte par défaut",
                                                  key=f"defaut_{fichier}")

                    if st.button("✅ Générer le visuel maintenant",
                                 key=f"gen_{fichier}", type="primary"):
                        with st.spinner("Génération du visuel..."):
                            # Déterminer la charte à utiliser
                            if utiliser_defaut:
                                from core.charte import charte_defaut as cd
                                charte_finale = cd()
                            elif upload:
                                img_pil       = Image.open(upload)
                                charte_finale = analyser_charte(img_pil)
                                sauvegarder_charte(charte_finale)
                                st.info("Charte extraite et sauvegardée !")
                            elif charte_existante:
                                charte_finale = charte_existante
                            else:
                                from core.charte import charte_defaut as cd
                                charte_finale = cd()

                            # Générer le visuel
                            nom_f   = fichier.replace("data/articles\\","").replace("data/articles/","").replace(".json","")
                            chemin  = generer_visuel(art, nom_f, charte_finale)

                            # Marquer comme publié
                            sauvegarder_statut(fichier, "publié")
                            st.session_state.pop(f"publier_{fichier}", None)

                        st.success("✅ Visuel généré !")
                        # Afficher le visuel généré
                        img_result = Image.open(chemin)
                        st.image(img_result, caption="Visuel généré", use_column_width=True)
                        st.markdown(f"📁 Sauvegardé dans : `{chemin}`")
                        st.rerun()

                    if st.button("Annuler", key=f"ann_{fichier}"):
                        st.session_state.pop(f"publier_{fichier}", None)
                        st.rerun()

            elif statut == "rejeté":
                if st.button("↩️ Remettre en attente", key=f"restaurer_{fichier}"):
                    sauvegarder_statut(fichier, "en_attente")
                    st.rerun()


# ─────────────────────────────────────────
# PAGE 4 — CHARTE GRAPHIQUE
# ─────────────────────────────────────────
elif page == "🎨 Charte graphique":
    st.title("🎨 Gestion de la charte graphique")
    st.markdown("Upload une image modèle pour que l'app reproduise automatiquement tes couleurs.")
    st.divider()

    col_gauche, col_droite = st.columns([1, 1])

    with col_gauche:
        st.subheader("📤 Uploader une image modèle")
        st.markdown("""
        Tu peux uploader :
        - Une **capture d'écran** de ton site
        - Un **article existant** que tu aimes
        - Ta **charte graphique officielle**
        - N'importe quelle **image avec tes couleurs**
        """)

        upload = st.file_uploader(
            "Choisis une image (JPG ou PNG)",
            type=["jpg","jpeg","png"]
        )

        if upload:
            img_pil = Image.open(upload)
            st.image(img_pil, caption="Image uploadée", use_column_width=True)

            if st.button("🔍 Analyser et sauvegarder cette charte", type="primary"):
                with st.spinner("Analyse en cours..."):
                    charte = analyser_charte(img_pil)
                    sauvegarder_charte(charte)

                st.success("✅ Charte analysée et sauvegardée !")
                st.session_state["charte_analysee"] = charte
                st.rerun()

    with col_droite:
        st.subheader("🎨 Charte actuelle")
        charte = charger_charte()

        if not charte:
            st.info("Aucune charte sauvegardée. Upload une image à gauche.")
            charte = charte_defaut()
            st.markdown("**Charte par défaut utilisée :**")

        # Afficher la palette
        couleurs = charte.get("couleurs", {})
        palette  = charte.get("palette",  [])

        st.markdown("**Palette extraite :**")
        nb_cols = min(len(palette), 6)
        if nb_cols > 0:
            cols = st.columns(nb_cols)
            for i, c in enumerate(palette[:nb_cols]):
                r, g, b = int(c[0]), int(c[1]), int(c[2])
                hex_c   = f'#{r:02x}{g:02x}{b:02x}'
                cols[i].markdown(
                    f'<div style="background:{hex_c}; width:100%; height:50px;'
                    f'border-radius:8px; margin-bottom:4px;"></div>'
                    f'<center><small><b>{hex_c}</b></small></center>',
                    unsafe_allow_html=True
                )

        st.markdown("")
        st.markdown("**Rôles des couleurs :**")
        roles = {
            "header":     "En-tête",
            "principale": "Couleur principale",
            "accent":     "Accent",
            "fond":       "Fond",
            "texte":      "Texte",
            "footer":     "Pied de page",
            "tag1":       "Tag 1",
            "tag2":       "Tag 2",
            "tag3":       "Tag 3",
        }
        for cle, nom in roles.items():
            c = couleurs.get(cle)
            if c:
                r, g, b = int(c[0]), int(c[1]), int(c[2])
                hex_c   = f'#{r:02x}{g:02x}{b:02x}'
                st.markdown(
                    f'<div style="display:flex; align-items:center; margin:4px 0;">'
                    f'<div style="background:{hex_c}; width:24px; height:24px;'
                    f'border-radius:4px; margin-right:10px; border:1px solid #ddd;"></div>'
                    f'<span><b>{nom}</b> — {hex_c}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # Structure détectée
        st.markdown("")
        st.markdown("**Structure détectée :**")
        structure = charte.get("structure", {})
        st.json({
            "Format":         "Paysage" if structure.get("format_paysage") else "Portrait",
            "Hauteur header": f"{structure.get('hauteur_header', 100)}px",
            "Image à gauche": structure.get("image_a_gauche", True),
        })

        # Générer un article test
        st.divider()
        if st.button("🧪 Générer un article test avec cette charte"):
            article_test = {
                "genere": {
                    "titre":         "Test de charte graphique",
                    "contenu":       "<p>Ceci est un article de test pour vérifier le rendu de votre charte graphique. Les couleurs, la typographie et la mise en page sont extraites automatiquement depuis votre image modèle.</p>",
                    "extrait":       "Test de génération avec charte personnalisée.",
                    "tags":          ["test", "charte", "numérique"],
                    "image_url":     None,
                    "image_credit":  "",
                },
                "source": {
                    "source": "Test",
                    "lien":   "https://example.com",
                    "titre":  "Test",
                    "resume": "Test",
                }
            }
            with st.spinner("Génération..."):
                chemin = generer_visuel(article_test, "test_charte", charte)
            st.success("✅ Article test généré !")
            st.image(Image.open(chemin), use_column_width=True)

    st.divider()

    # Visuels générés
    st.subheader("📁 Visuels générés")
    fichiers_jpg = glob.glob("output/articles_ok/*.jpg")
    if fichiers_jpg:
        fichiers_jpg.sort(key=os.path.getmtime, reverse=True)
        cols = st.columns(3)
        for i, f in enumerate(fichiers_jpg[:9]):
            with cols[i % 3]:
                img = Image.open(f)
                st.image(img, caption=os.path.basename(f), use_column_width=True)
    else:
        st.info("Aucun visuel généré pour l'instant. Publie un article dans l'onglet Articles.")
