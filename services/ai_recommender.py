import os
import json
from anthropic import Anthropic

def get_ai_recommendation(menus, user_preference=""):
    """Minta Claude rekomendasiin menu."""
    if not menus:
        return {"recommendations": [], "reason": "Belum ada menu"}

    menu_list = "\n".join([
        f"- ID {m.id}: {m.name} (Rp{m.price:,}) - {m.category} - "
        f"{m.description or 'tanpa deskripsi'}"
        f"{' [TERLARIS]' if m.is_bestseller else ''}"
        for m in menus if m.is_available
    ])

    prompt = f"""Kamu adalah asisten rekomendasi menu warung.

Daftar menu:
{menu_list}

Preferensi pembeli: {user_preference or "rekomendasikan menu populer"}

Rekomendasikan 3 menu terbaik. Jawab HANYA dengan JSON:
{{"recommendations": [id1, id2, id3], "reason": "alasan singkat"}}"""

    try:
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        # Fallback ke bestseller
        bestsellers = [m.id for m in menus if m.is_bestseller][:3]
        return {"recommendations": bestsellers, "reason": "Menu terlaris kami"}