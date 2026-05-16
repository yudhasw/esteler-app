"""
Entry point untuk pengembangan LOKAL.
Untuk Vercel deployment, lihat api/index.py.

Cara pakai:
    python app.py            # langsung jalan
    flask --app app run      # via flask CLI
"""
from api.index import app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
