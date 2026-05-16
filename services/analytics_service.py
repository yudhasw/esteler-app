"""
AnalyticsService - data untuk dashboard admin

FILE BARU (sebelumnya MISSING walaupun di-import di admin.py).

Menyediakan agregat data untuk dashboard:
- Total revenue, orders, customers
- Top menu, weekly revenue
- Distribusi sumber order (online vs walkin) - sesuai SDD
- Jam paling ramai - sesuai SDD

Optimasi:
- Pakai SQL aggregation (SUM, COUNT, GROUP BY) BUKAN load semua row ke Python
- 1 query untuk dashboard summary (lebih cepet daripada banyak query terpisah)
"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from sqlalchemy import func, case
from models import db, Order, OrderItem, Menu


class AnalyticsService:

    @staticmethod
    def _today_start():
        return datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    @staticmethod
    def get_dashboard_summary() -> Dict:
        """
        Ringkasan untuk dashboard admin (yang muncul di halaman utama).
        Dipakai oleh routes/admin.py.
        """
        today = AnalyticsService._today_start()
        week_ago = today - timedelta(days=7)
        last_week = today - timedelta(days=14)

        # Hari ini
        today_revenue, today_orders = db.session.query(
            func.coalesce(func.sum(Order.total), 0),
            func.count(Order.id),
        ).filter(
            Order.created_at >= today,
            Order.status != "dibatalkan",
        ).first()

        # Minggu ini vs minggu lalu (untuk persentase growth)
        week_revenue = db.session.query(
            func.coalesce(func.sum(Order.total), 0)
        ).filter(
            Order.created_at >= week_ago,
            Order.status != "dibatalkan",
        ).scalar()

        last_week_revenue = db.session.query(
            func.coalesce(func.sum(Order.total), 0)
        ).filter(
            Order.created_at >= last_week,
            Order.created_at < week_ago,
            Order.status != "dibatalkan",
        ).scalar()

        # Hitung growth %
        if last_week_revenue > 0:
            growth = ((week_revenue - last_week_revenue) / last_week_revenue) * 100
        else:
            growth = 0.0

        return {
            "today_revenue": int(today_revenue or 0),
            "today_orders": int(today_orders or 0),
            "week_revenue": int(week_revenue or 0),
            "revenue_growth_percent": round(growth, 1),
            "active_orders": Order.query.filter(
                Order.status.in_(["menunggu", "memasak", "siap"])
            ).count(),
            "total_menus": Menu.query.filter_by(is_active=True).count(),
            "completed_today": Order.query.filter(
                Order.status == "selesai", Order.created_at >= today
            ).count(),
        }

    @staticmethod
    def get_top_menus(limit: int = 5, days: int = 30) -> List[Dict]:
        """
        Menu terlaris berdasarkan jumlah terjual dalam N hari terakhir.
        SQL aggregation - tidak load semua order_items ke Python.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        results = (
            db.session.query(
                Menu.id,
                Menu.name,
                Menu.image_url,
                Menu.price,
                func.sum(OrderItem.quantity).label("sold"),
            )
            .join(OrderItem, OrderItem.menu_id == Menu.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                Order.created_at >= since,
                Order.status != "dibatalkan",
            )
            .group_by(Menu.id, Menu.name, Menu.image_url, Menu.price)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": r.id,
                "name": r.name,
                "image_url": r.image_url,
                "price": r.price,
                "sold": int(r.sold),
            }
            for r in results
        ]

    @staticmethod
    def get_weekly_revenue() -> List[Dict]:
        """
        Revenue per hari dalam 7 hari terakhir (untuk chart).
        SQL GROUP BY date - efisien.
        """
        since = AnalyticsService._today_start() - timedelta(days=6)

        results = (
            db.session.query(
                func.date(Order.created_at).label("date"),
                func.coalesce(func.sum(Order.total), 0).label("revenue"),
            )
            .filter(
                Order.created_at >= since,
                Order.status != "dibatalkan",
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
            .all()
        )

        # Map hasil ke dict
        data_map = {str(r.date): int(r.revenue) for r in results}

        # Generate 7 hari terakhir (include hari yang tidak ada order)
        labels = ["SEN", "SEL", "RAB", "KAM", "JUM", "SAB", "MIN"]
        output = []
        for i in range(7):
            d = (AnalyticsService._today_start() - timedelta(days=6 - i)).date()
            output.append({
                "date": str(d),
                "label": labels[d.weekday()],
                "revenue": data_map.get(str(d), 0),
            })
        return output

    @staticmethod
    def get_order_source_distribution(days: int = 30) -> Dict:
        """
        Distribusi sumber order: ONLINE_PREORDER vs WALKIN.
        Sesuai SDD revisi.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        results = (
            db.session.query(
                Order.order_source,
                func.count(Order.id).label("count"),
                func.coalesce(func.sum(Order.total), 0).label("revenue"),
            )
            .filter(
                Order.created_at >= since,
                Order.status != "dibatalkan",
            )
            .group_by(Order.order_source)
            .all()
        )
        return {
            r.order_source: {"count": int(r.count), "revenue": int(r.revenue)}
            for r in results
        }

    @staticmethod
    def get_peak_hours(days: int = 30) -> List[Dict]:
        """
        Jam paling ramai (sesuai SDD).
        Aggregate by hour-of-day dalam N hari terakhir.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        results = (
            db.session.query(
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count"),
            )
            .filter(
                Order.created_at >= since,
                Order.status != "dibatalkan",
            )
            .group_by(func.extract("hour", Order.created_at))
            .order_by(func.count(Order.id).desc())
            .all()
        )
        return [{"hour": int(r.hour), "count": int(r.count)} for r in results]
