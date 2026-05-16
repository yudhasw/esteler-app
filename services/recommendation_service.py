"""
RecommendationService - rekomendasi menu untuk customer

FILE BARU (sebelumnya MISSING walaupun di-import di customer.py).

Approach: Rule-based dengan match score (mudah upgrade ke Decision Tree nanti).
- Cek cache dulu di tabel recommendations (sesuai SDD: expires_at)
- Kalau cache expired/empty: generate baru
- Scoring: berdasarkan bestseller flag, sold_count, rating, dan match dengan
  history cart customer

Kenapa rule-based dulu, BUKAN scikit-learn?
1. scikit-learn butuh dataset training yang cukup
2. Load model joblib di Vercel cold start = +1-2 detik per request
3. Untuk MVP, rule-based sudah cukup memberikan rekomendasi yang relevan
4. Struktur code di-design supaya gampang ditukar ke Decision Tree nanti
   (cukup ganti _calculate_match_score)
"""
from datetime import timedelta
from typing import List
from sqlalchemy.orm import joinedload
from models import db, Menu, Recommendation, CartItem, Cart, now_utc


CACHE_DURATION = timedelta(hours=1)
TOP_N = 5


class RecommendationService:

    @staticmethod
    def get_recommendations(session_id: str, limit: int = TOP_N) -> List[dict]:
        """
        Entry point utama (dipanggil dari routes/customer.py).
        Cek cache dulu, generate baru kalau perlu.
        """
        cached = RecommendationService._get_cached(session_id)
        if cached:
            return [r.to_dict() for r in cached[:limit]]

        # Generate baru
        recos = RecommendationService.generate_for_session(session_id, limit)
        return [r.to_dict() for r in recos]

    @staticmethod
    def _get_cached(session_id: str) -> List[Recommendation]:
        """Ambil cache rekomendasi yang masih valid (belum expired)."""
        return (
            Recommendation.query.options(joinedload(Recommendation.menu))
            .filter(
                Recommendation.session_id == session_id,
                Recommendation.expires_at > now_utc(),
            )
            .order_by(Recommendation.match_score.desc())
            .all()
        )

    @staticmethod
    def generate_for_session(session_id: str, limit: int = TOP_N) -> List[Recommendation]:
        """
        Generate rekomendasi baru dan simpan ke DB sebagai cache.
        Algoritma: rule-based scoring.
        """
        # 1. Clean cache lama untuk session ini
        Recommendation.query.filter_by(session_id=session_id).delete()

        # 2. Ambil semua menu aktif
        menus = Menu.query.filter_by(is_active=True).all()
        if not menus:
            db.session.commit()
            return []

        # 3. Get cart history (untuk personalization)
        cart_categories = RecommendationService._get_user_preferred_categories(session_id)

        # 4. Score tiap menu
        scored = []
        for menu in menus:
            score, reason = RecommendationService._calculate_match_score(
                menu, cart_categories
            )
            scored.append((menu, score, reason))

        # 5. Sort dan ambil top-N
        scored.sort(key=lambda x: x[1], reverse=True)
        top_n = scored[:limit]

        # 6. Simpan ke cache
        expires = now_utc() + CACHE_DURATION
        recos = []
        for menu, score, reason in top_n:
            r = Recommendation(
                menu_id=menu.id,
                session_id=session_id,
                match_score=score,
                reason=reason,
                expires_at=expires,
            )
            db.session.add(r)
            recos.append(r)

        db.session.commit()

        # Re-fetch dengan eager load menu (biar to_dict bisa akses menu data)
        return RecommendationService._get_cached(session_id)

    @staticmethod
    def _get_user_preferred_categories(session_id: str) -> dict:
        """
        Hitung kategori favorit user berdasarkan history cart.
        Return: {category: count}
        """
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            return {}

        items = (
            CartItem.query.options(joinedload(CartItem.menu))
            .filter_by(cart_id=cart.id)
            .all()
        )

        prefs = {}
        for item in items:
            if item.menu and item.menu.category:
                prefs[item.menu.category] = prefs.get(item.menu.category, 0) + item.quantity
        return prefs

    @staticmethod
    def _calculate_match_score(menu: Menu, user_categories: dict) -> tuple:
        """
        Hitung match score (0.0 - 1.0) + reason.

        Faktor:
        - Best seller flag: +0.30
        - Favorite flag: +0.20
        - High sold count: +0.15 (relatif)
        - High rating: +0.15 (relatif)
        - Match kategori favorit user: +0.20
        Base: 0.30
        """
        score = 0.30  # Base score
        reasons = []

        if menu.is_best_seller:
            score += 0.30
            reasons.append("terlaris")

        if menu.is_favorite:
            score += 0.20
            reasons.append("favorit")

        # Sold count factor (max +0.15)
        if menu.sold_count and menu.sold_count > 50:
            score += 0.15
            reasons.append("banyak peminat")
        elif menu.sold_count and menu.sold_count > 10:
            score += 0.08

        # Rating factor (max +0.15)
        if menu.rating and menu.rating >= 4.5:
            score += 0.15
            reasons.append(f"rating tinggi {menu.rating}")
        elif menu.rating and menu.rating >= 4.0:
            score += 0.08

        # Kategori match
        if menu.category and menu.category in user_categories:
            score += 0.20
            reasons.append(f"sesuai preferensi {menu.category}")

        # Clamp ke max 1.0
        score = min(score, 1.0)

        reason = ", ".join(reasons) if reasons else "rekomendasi umum"
        return score, reason
