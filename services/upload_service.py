"""
UploadService - upload gambar menu ke Cloudinary

Cloudinary dipilih karena free tier-nya permanen (25 credit/bulan,
~25GB kombinasi storage+bandwidth) dan tidak butuh filesystem lokal
(cocok untuk deployment serverless di Vercel).
"""
from typing import Optional
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from werkzeug.datastructures import FileStorage

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


class UploadService:
    @staticmethod
    def is_allowed(filename: str) -> bool:
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    @staticmethod
    def upload_menu_image(file: FileStorage) -> Optional[str]:
        """
        Upload gambar menu ke Cloudinary, return secure URL.
        Raise ValueError kalau format tidak didukung atau upload gagal.
        """
        if not file or not file.filename:
            return None

        if not UploadService.is_allowed(file.filename):
            raise ValueError("Format gambar tidak didukung (gunakan JPG, PNG, WEBP, atau GIF).")

        try:
            result = cloudinary.uploader.upload(
                file,
                folder="dapur-hijrah/menu",
                resource_type="image",
            )
        except CloudinaryError as e:
            raise ValueError(f"Upload gambar gagal: {e}")

        return result["secure_url"]
