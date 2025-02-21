from flask import Flask, request, render_template
from textblob import TextBlob
from collections import Counter
import re
import matplotlib.pyplot as plt
import os
from fpdf import FPDF
import tweepy
import praw
from datetime import datetime

app = Flask(__name__)

# Fonction pour récupérer les posts depuis les API
def recuperer_posts(mot_cle, reseau, api_keys, max_results=20):
    """Récupère les posts d'un réseau social avec les clés API fournies."""
    try:
        if reseau == "twitter":
            bearer_token = api_keys.get("twitter_bearer_token")
            if not bearer_token:
                raise ValueError("Bearer Token requis pour Twitter.")
            client = tweepy.Client(bearer_token=bearer_token)
            tweets = client.search_recent_tweets(query=mot_cle, max_results=max_results, tweet_fields=["created_at"])
            return [{"text": tweet.text, "created_at": tweet.created_at.strftime("%Y-%m-%d %H:%M")} for tweet in tweets.data] if tweets.data else []
        
        elif reseau == "reddit":
            client_id = api_keys.get("reddit_client_id")
            client_secret = api_keys.get("reddit_client_secret")
            user_agent = api_keys.get("reddit_user_agent", "mon_saas/1.0")
            if not (client_id and client_secret):
                raise ValueError("Client ID et Secret requis pour Reddit.")
            reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
            posts = reddit.subreddit("all").search(mot_cle, limit=max_results)
            return [{"text": post.title + " " + post.selftext, "created_at": datetime.fromtimestamp(post.created_utc).strftime("%Y-%m-%d %H:%M")} for post in posts]
        
        elif reseau == "instagram" or reseau == "facebook":
            # Placeholder pour Instagram/Facebook (Graph API non implémenté)
            return []
        
        return []
    except Exception as e:
        raise e

# Analyse de sentiment
def analyser_sentiment(texte):
    """Classe le sentiment d'un texte en Positif, Négatif ou Neutre."""
    blob = TextBlob(texte)
    polarite = blob.sentiment.polarity
    return "Positif" if polarite > 0 else "Négatif" if polarite < 0 else "Neutre"

# Extraction des mots clés
def extraire_mots(posts):
    """Extrait les mots ou hashtags significatifs des posts."""
    mots = []
    for post in posts:
        texte = re.sub(r"http\S+|www\S+|https\S+", "", post["text"], flags=re.MULTILINE)
        mots.extend([mot.lower() for mot in texte.split() if mot.startswith("#") or len(mot) > 3])
    return mots

# Calcul des statistiques
def calculer_stats(posts):
    """Calcule des statistiques avancées sur les posts."""
    sentiments = {"Positif": 0, "Négatif": 0, "Neutre": 0}
    longueurs = []
    mots_positifs = []
    mots_negatifs = []
    heures = {}
    
    for post in posts:
        sentiment = analyser_sentiment(post["text"])
        sentiments[sentiment] += 1
        longueurs.append(len(post["text"]))
        mots = extraire_mots([post])
        if sentiment == "Positif":
            mots_positifs.extend(mots)
        elif sentiment == "Négatif":
            mots_negatifs.extend(mots)
        heure = post["created_at"].split(" ")[1].split(":")[0]
        heures[heure] = heures.get(heure, 0) + 1
    
    total = len(posts)
    stats = {
        "total": total,
        "positif_pct": (sentiments["Positif"] / total) * 100 if total > 0 else 0,
        "negatif_pct": (sentiments["Négatif"] / total) * 100 if total > 0 else 0,
        "neutre_pct": (sentiments["Neutre"] / total) * 100 if total > 0 else 0,
        "longueur_moyenne": sum(longueurs) / total if total > 0 else 0,
        "mots_positifs": Counter(mots_positifs).most_common(5),
        "mots_negatifs": Counter(mots_negatifs).most_common(5),
        "frequence_heures": heures
    }
    return sentiments, stats

# Création des graphiques
def creer_graphique_sentiments(sentiments):
    """Génère un camembert des sentiments."""
    plt.figure(figsize=(6, 6))
    plt.pie(sentiments.values(), labels=sentiments.keys(), autopct='%1.1f%%', startangle=90, colors=["#4CAF50", "#F44336", "#FFC107"])
    plt.title("Répartition des Sentiments")
    plt.savefig("static/sentiments.png", bbox_inches="tight")
    plt.close()

def creer_graphique_tendances(tendances):
    """Génère un graphique en barres des tendances."""
    mots, freqs = zip(*tendances)
    plt.figure(figsize=(10, 6))
    plt.bar(mots, freqs, color="skyblue")
    plt.title("Top 5 Tendances")
    plt.xlabel("Mots")
    plt.ylabel("Fréquence")
    plt.xticks(rotation=45)
    plt.savefig("static/tendances.png", bbox_inches="tight")
    plt.close()

def creer_graphique_heures(heures):
    """Génère une courbe de fréquence par heure."""
    heures_triees = dict(sorted(heures.items()))
    plt.figure(figsize=(10, 6))
    plt.plot(list(heures_triees.keys()), list(heures_triees.values()), marker="o", color="purple")
    plt.title("Fréquence par Heure")
    plt.xlabel("Heure")
    plt.ylabel("Nombre de Posts")
    plt.grid(True)
    plt.savefig("static/heures.png", bbox_inches="tight")
    plt.close()

# Export en PDF
def exporter_pdf(stats, tendances, reseau, mot_cle):
    """Crée un rapport PDF avec les résultats."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Analyse Sociale - {reseau.capitalize()} - {mot_cle}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.cell(200, 10, txt=f"Total de posts : {stats['total']}", ln=True)
    pdf.cell(200, 10, txt=f"Positif : {stats['positif_pct']:.1f}%", ln=True)
    pdf.cell(200, 10, txt=f"Négatif : {stats['negatif_pct']:.1f}%", ln=True)
    pdf.cell(200, 10, txt=f"Neutre : {stats['neutre_pct']:.1f}%", ln=True)
    pdf.cell(200, 10, txt=f"Longueur moyenne : {stats['longueur_moyenne']:.1f} caractères", ln=True)
    
    pdf.ln(10)
    pdf.cell(200, 10, txt="Top Mots Positifs :", ln=True)
    for mot, freq in stats["mots_positifs"]:
        pdf.cell(200, 10, txt=f"{mot} ({freq})", ln=True)
    
    pdf.cell(200, 10, txt="Top Mots Négatifs :", ln=True)
    for mot, freq in stats["mots_negatifs"]:
        pdf.cell(200, 10, txt=f"{mot} ({freq})", ln=True)
    
    pdf.output("static/rapport.pdf")

# Route principale
@app.route("/", methods=["GET", "POST"])
def index():
    """Affiche le formulaire ou traite les données."""
    if request.method == "POST":
        mot_cle = request.form["mot_cle"]
        reseau = request.form["reseau"]
        
        # Clés API depuis le formulaire
        api_keys = {
            "twitter_bearer_token": request.form.get("twitter_bearer_token", ""),
            "reddit_client_id": request.form.get("reddit_client_id", ""),
            "reddit_client_secret": request.form.get("reddit_client_secret", ""),
            "reddit_user_agent": request.form.get("reddit_user_agent", "mon_saas/1.0")
        }
        
        try:
            posts = recuperer_posts(mot_cle, reseau, api_keys)
            if not posts:
                return render_template("index.html", erreur=f"Aucun post trouvé sur {reseau} pour '{mot_cle}'. Vérifiez vos clés API.")
            
            sentiments, stats = calculer_stats(posts)
            tendances = Counter(extraire_mots(posts)).most_common(5)
            
            if not os.path.exists("static"):
                os.makedirs("static")
            creer_graphique_sentiments(sentiments)
            creer_graphique_tendances(tendances)
            creer_graphique_heures(stats["frequence_heures"])
            exporter_pdf(stats, tendances, reseau, mot_cle)
            
            return render_template("resultats.html", stats=stats, tendances=tendances, reseau=reseau, mot_cle=mot_cle)
        except Exception as e:
            return render_template("index.html", erreur=f"Erreur : {str(e)}")
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)