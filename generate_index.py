"""
Rigenera index.html a partire dai dati e dalla logica in app.py.

Uso:
    python generate_index.py

Va eseguito nella stessa cartella dove si trova app.py.
Ogni volta che modifichi le disponibilita' o la logica in app.py,
rilancia questo script per aggiornare index.html, poi ricaricalo su GitHub.
"""

from app import render_html

with open("index.html", "w", encoding="utf-8") as f:
    f.write(render_html())

print("index.html generato con successo nella cartella corrente.")