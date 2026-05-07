class ReportService:
    @staticmethod
    def generate_pdf(start_date, end_date):
        """Menghasilkan file laporan PDF (Stub)."""
        # Nantinya di sini kita bisa menggunakan FPDF atau ReportLab
        return b"MOCK_PDF_DATA_FOR_REPORT"

    @staticmethod
    def generate_csv(start_date, end_date):
        """Menghasilkan file CSV (Stub)."""
        import csv
        import io
        from models import Order

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Order ID", "Kode", "Total", "Status", "Tanggal"])

        orders = (
            Order.query.all()
        )  # Idealnya difilter berdasarkan start_date & end_date
        for o in orders:
            writer.writerow([o.id, o.order_code, o.total, o.status, o.created_at])

        return output.getvalue()

    @staticmethod
    def export_orders(filters):
        return b"MOCK_EXPORT_FILE"
