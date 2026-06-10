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

        # Total Keseluruhan (All time)
        total_revenue = db.session.query(
            func.coalesce(func.sum(Order.total), 0)
        ).filter(
            Order.status == "selesai",
        ).scalar()
        
        total_orders = db.session.query(
            func.coalesce(func.sum(OrderItem.quantity), 0)
        ).join(Order, Order.id == OrderItem.order_id).filter(
            Order.status == "selesai",
        ).scalar()
        
        # Kepuasan (Average rating menu)
        satisfaction = db.session.query(
            func.avg(Menu.rating)
        ).filter(Menu.rating > 0).scalar()
        satisfaction_score = round(satisfaction, 1) if satisfaction else 0.0
        satisfaction_percent = int((satisfaction_score / 5.0) * 100) if satisfaction_score > 0 else 0

        # Minggu ini vs minggu lalu (untuk persentase growth)
        week_revenue = db.session.query(
            func.coalesce(func.sum(Order.total), 0)
        ).filter(
            Order.created_at >= week_ago,
            Order.status == "selesai",
        ).scalar()

        last_week_revenue = db.session.query(
            func.coalesce(func.sum(Order.total), 0)
        ).filter(
            Order.created_at >= last_week,
            Order.created_at < week_ago,
            Order.status == "selesai",
        ).scalar()

        # Hitung growth %
        if last_week_revenue > 0:
            growth = ((week_revenue - last_week_revenue) / last_week_revenue) * 100
        else:
            growth = 0.0

        return {
            "total_revenue": int(total_revenue or 0),
            "total_orders": int(total_orders or 0),
            "week_revenue": int(week_revenue or 0),
            "revenue_growth_percent": round(growth, 1),
            "active_orders": Order.query.filter(
                Order.status.in_(["menunggu", "memasak", "siap"])
            ).count(),
            "total_menus": Menu.query.filter_by(is_active=True).count(),
            "completed_today": Order.query.filter(
                Order.status == "selesai", Order.created_at >= today
            ).count(),
            "satisfaction_score": satisfaction_score,
            "satisfaction_percent": satisfaction_percent,
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
                Order.status == "selesai",
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
        Revenue per hari dalam 7 hari terakhir (minggu ini) dan 7 hari sebelumnya (minggu lalu).
        """
        today = AnalyticsService._today_start()
        since_last_week = today - timedelta(days=13)

        results = (
            db.session.query(
                func.date(Order.created_at).label("date"),
                func.coalesce(func.sum(Order.total), 0).label("revenue"),
            )
            .filter(
                Order.created_at >= since_last_week,
                Order.status == "selesai",
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
            d_this = (today - timedelta(days=6 - i)).date()
            d_last = (today - timedelta(days=13 - i)).date()
            output.append({
                "date": str(d_this),
                "label": labels[d_this.weekday()],
                "revenue": data_map.get(str(d_this), 0),
                "last_revenue": data_map.get(str(d_last), 0),
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
                Order.status == "selesai",
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
                Order.status == "selesai",
            )
            .group_by(func.extract("hour", Order.created_at))
            .order_by(func.count(Order.id).desc())
            .all()
        )
        return [{"hour": int(r.hour), "count": int(r.count)} for r in results]
