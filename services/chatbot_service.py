"""
ChatbotService - asisten chat pemesanan berbasis Groq (tool-calling)

Perubahan dari versi sebelumnya:
- Checkout (siapkan_pesanan, buat_pesanan, batalkan_pesanan) dipindah ke UI.
- Tools berkurang dari 11 → 7.
- System prompt dipangkas ~50%.
- Tidak ada lagi draft/session state di server.
- Response mengembalikan show_checkout=True sebagai sinyal ke frontend
  untuk menampilkan panel checkout yang sudah terisi dari keranjang.
- History dipangkas ke MAX_HISTORY pesan terakhir untuk hemat token.
- Tool result cari_menu/lihat_menu hanya return field yang dibutuhkan model.
"""

import json
import re
from groq import Groq, BadRequestError
from flask import current_app

from services.menu_service import MenuService
from services.cart_service import CartService
from services.order_service import OrderService
from services.recommendation_service import RecommendationService

MAX_TOOL_ITERATIONS = 8
MAX_HISTORY = 12  # pesan user+assistant yang dikirim ke API (hemat token)

SYSTEM_PROMPT = """Kamu adalah asisten virtual Dapur Hijrah, toko Es Teler online.
Tugasmu: membantu pelanggan menemukan menu dan mengisi keranjang belanja. Checkout dilakukan di halaman terpisah.

ATURAN TOOL - WAJIB DIIKUTI:
- JANGAN PERNAH menjelaskan atau mendeskripsikan menu dari pengetahuanmu sendiri.
  Semua info menu (nama, harga, deskripsi, varian) HARUS dari hasil tool.
- Jika pelanggan menyebut jenis minuman, rasa, atau kata sifat apapun (segar, manis,
  buah, coklat, dll) → LANGSUNG panggil cari_menu atau lihat_menu. Jangan jelaskan
  dulu, jangan tanya izin dulu, langsung panggil tool.
- Jika keyword terlalu umum atau hasil cari_menu kosong/tidak relevan → langsung
  panggil lihat_menu (tanpa category) untuk tampilkan semua menu yang tersedia.
  Jangan bilang "tidak ditemukan" sebelum mencoba lihat_menu.
- Jika pelanggan tanya detail spesifik tentang satu atau beberapa menu (kandungan,
  bahan, rasa, "ada buahnya tidak?", "apa isinya?") → panggil detail_menu dengan
  menu_id yang relevan. Jangan mengarang jawaban dari pengetahuanmu sendiri.
- JANGAN PERNAH tanya "apakah kamu ingin saya carikan?" atau "mau saya cek dulu?" —
  langsung cari tanpa minta konfirmasi.
- JANGAN menebak menu_id atau item_id. Untuk tambah_ke_keranjang, selalu panggil
  cari_menu/lihat_menu dulu. Untuk ubah/hapus item, panggil lihat_keranjang dulu.
- Jika pencarian menghasilkan lebih dari satu menu yang cocok, tampilkan hasilnya
  lalu tanya pelanggan mana yang dimaksud — baru tambahkan ke keranjang.

ATURAN BALASAN:
- Ringkas. Maksimal 1-2 kalimat sebelum atau sesudah menampilkan hasil tool.
- Jangan berpanjang-panjang menjelaskan sesuatu yang bisa ditunjukkan langsung.
- Saat menampilkan daftar menu, tulis setiap item di baris baru dengan format:
  "Nama Menu - Rp harga"
  Jangan gabungkan semua nama dalam satu kalimat panjang.
- Tanpa markdown (tidak perlu **tebal** atau #heading). Bahasa Indonesia santai.
- Jika di luar topik Dapur Hijrah, arahkan kembali dengan sopan dan singkat.

ALUR CHECKOUT:
- Setelah pelanggan setuju dengan isi keranjang, sampaikan singkat bahwa form
  checkout akan muncul. Sistem otomatis menampilkan panel checkout.
- Kamu TIDAK perlu tanya nama, kontak, atau metode pembayaran — itu diisi di form.
- Untuk lacak pesanan, gunakan tool lacak_pesanan dengan kode ORD-YYYYMMDD-XXXX.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "cari_menu",
            "description": (
                "Cari menu berdasarkan kata kunci nama atau rasa "
                "(misal 'durian', 'alpukat', 'original'). "
                "Gunakan sebelum tambah_ke_keranjang untuk mendapat menu_id valid."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Kata kunci pencarian"}
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lihat_menu",
            "description": "Lihat daftar semua menu atau filter per kategori.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Nama kategori (opsional). Kosongkan untuk semua menu.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rekomendasi_menu",
            "description": "Dapatkan rekomendasi menu terbaik berdasarkan popularitas dan rating.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lihat_keranjang",
            "description": "Lihat isi keranjang belanja pelanggan saat ini.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tambah_ke_keranjang",
            "description": (
                "Tambah menu ke keranjang. Gunakan menu_id dari hasil "
                "cari_menu/lihat_menu/rekomendasi_menu - jangan tebak ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "menu_id": {
                        "type": "integer",
                        "description": "ID menu (dari hasil pencarian)",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Jumlah porsi (default 1)",
                    },
                },
                "required": ["menu_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ubah_jumlah_keranjang",
            "description": "Ubah quantity item di keranjang. Gunakan item_id dari lihat_keranjang.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "ID item keranjang"},
                    "quantity": {
                        "type": "integer",
                        "description": "Jumlah baru. 0 = hapus item.",
                    },
                },
                "required": ["item_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hapus_dari_keranjang",
            "description": "Hapus item dari keranjang. Gunakan item_id dari lihat_keranjang.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "ID item keranjang"}
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detail_menu",
            "description": (
                "Ambil detail lengkap satu menu: deskripsi, bahan, rasa, rating. "
                "Gunakan saat pelanggan tanya kandungan/detail menu tertentu "
                "(misal 'ada buahnya tidak?', 'apa isinya?', 'rasanya gimana?'). "
                "Gunakan menu_id dari hasil cari_menu atau lihat_menu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "menu_id": {
                        "type": "integer",
                        "description": "ID menu (dari hasil cari_menu/lihat_menu)",
                    }
                },
                "required": ["menu_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lacak_pesanan",
            "description": "Lacak status pesanan berdasarkan kode (format ORD-YYYYMMDD-XXXX).",
            "parameters": {
                "type": "object",
                "properties": {
                    "kode_pesanan": {
                        "type": "string",
                        "description": "Kode pesanan, contoh ORD-20260615-AB12",
                    }
                },
                "required": ["kode_pesanan"],
            },
        },
    },
]

# Kata-kata yang menandakan pelanggan siap checkout
_CHECKOUT_SIGNALS = re.compile(
    r"\b(checkout|pesan|beli|order|lanjut(\s+ke)?\s+(checkout|pembayaran|bayar)"
    r"|buka\s+(form|halaman)\s+checkout)\b",
    re.IGNORECASE,
)


def _menu_brief(menu) -> dict:
    """Hanya field yang benar-benar dibutuhkan model untuk menjawab."""
    return {
        "id": menu.id,
        "name": menu.name,
        "price": menu.price,
        "category": menu.category,
        "is_best_seller": menu.is_best_seller,
    }


def _menu_detail(menu) -> dict:
    """Versi lengkap, dipakai hanya saat pelanggan tanya detail spesifik."""
    return {
        "id": menu.id,
        "name": menu.name,
        "description": menu.description,
        "price": menu.price,
        "category": menu.category,
        "rating": menu.rating,
        "is_best_seller": menu.is_best_seller,
    }


# Beberapa model kadang menulis tool call sebagai teks biasa, contoh:
# "cari_menu minuman buah segar" atau "<function>cari_menu {...}</function>"
# Pattern ini mendeteksi format tersebut supaya tetap bisa dieksekusi.
_PSEUDO_FUNCTION_PATTERNS = [
    re.compile(r"<function\s*=\s*(\w+)\s*>\s*(\{.*?\})\s*</function>", re.DOTALL),
    re.compile(r"<function\s*>\s*(\w+)\s*(\{.*?\})\s*</function>", re.DOTALL),
]

# Nama tool valid
_VALID_TOOL_NAMES = {t["function"]["name"] for t in TOOLS}

# Alias parameter
_ARG_ALIASES = {
    "jumlah": "quantity",
    "qty": "quantity",
    "id_menu": "menu_id",
    "id_item": "item_id",
    "kode": "kode_pesanan",
    "order_code": "kode_pesanan",
}


def _extract_pseudo_tool_call(content: str):
    """Deteksi tool call yang ditulis sebagai teks biasa.

    Mendukung tiga format:
    1. Tag XML:   <function=nama>{...}</function>
    2. Inline:    nama_tool {"key": "val"}
    3. Plain:     nama_tool kata kunci tanpa JSON

    Return (nama_tool, args_dict) jika valid, else None.
    """
    if not content:
        return None

    # Format tag XML
    for pattern in _PSEUDO_FUNCTION_PATTERNS:
        m = pattern.search(content)
        if not m:
            continue
        name, args_str = m.group(1), m.group(2)
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            continue
        if not isinstance(args, dict):
            continue
        return name, {_ARG_ALIASES.get(k, k): v for k, v in args.items()}

    # Format inline: "nama_tool {json}" atau "nama_tool plain text"
    stripped = content.strip()
    parts = stripped.split(None, 1)
    if len(parts) >= 1 and parts[0] in _VALID_TOOL_NAMES:
        name = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else "{}"
        # Coba parse JSON
        try:
            args = json.loads(rest)
            if isinstance(args, dict):
                return name, {_ARG_ALIASES.get(k, k): v for k, v in args.items()}
        except json.JSONDecodeError:
            pass
        # Fallback plain text sebagai keyword
        if name in ("cari_menu", "lihat_menu") and rest:
            return name, {"keyword": rest}

    return None


def _execute_tool(name: str, args: dict, session_id: str) -> dict:
    if name == "cari_menu":
        menus = MenuService.search(args.get("keyword", ""))
        return {"menus": [_menu_brief(m) for m in menus]}

    if name == "lihat_menu":
        category = (args.get("category") or "").strip()
        menus = (
            MenuService.get_by_category(category) if category else MenuService.get_all()
        )
        return {"menus": [_menu_brief(m) for m in menus]}

    if name == "rekomendasi_menu":
        recos = RecommendationService.get_recommendations(session_id)
        return {
            "rekomendasi": [
                {
                    "id": r["menu"]["id"],
                    "name": r["menu"]["name"],
                    "price": r["menu"]["price"],
                    "alasan": r["reason"],
                }
                for r in recos
                if r.get("menu")
            ]
        }

    if name == "lihat_keranjang":
        return CartService.get_summary(session_id)

    if name == "tambah_ke_keranjang":
        try:
            item = CartService.add_item(
                session_id, int(args["menu_id"]), int(args.get("quantity", 1))
            )
        except (ValueError, KeyError, TypeError) as e:
            return {"success": False, "message": str(e)}
        menu = MenuService.get_by_id(item.menu_id)
        return {
            "success": True,
            "item_id": item.id,
            "menu": menu.name if menu else None,
            "quantity": item.quantity,
        }

    if name == "ubah_jumlah_keranjang":
        try:
            item = CartService.update_quantity(
                int(args["item_id"]), int(args["quantity"])
            )
        except (KeyError, TypeError, ValueError) as e:
            return {"success": False, "message": str(e)}
        if item:
            return {"success": True, "item_id": item.id, "quantity": item.quantity}
        return {"success": True, "message": "Item dihapus dari keranjang"}

    if name == "hapus_dari_keranjang":
        try:
            ok = CartService.remove_item(int(args["item_id"]))
        except (KeyError, TypeError, ValueError) as e:
            return {"success": False, "message": str(e)}
        return {"success": ok}

    if name == "lacak_pesanan":
        order = OrderService.get_by_code(args.get("kode_pesanan", "").strip())
        if not order:
            return {"found": False}
        return {
            "found": True,
            "order_code": order.order_code,
            "status": order.status,
            "total": order.total,
            "items": [
                {
                    "menu": item.menu.name if item.menu else None,
                    "quantity": item.quantity,
                    "subtotal": item.subtotal,
                }
                for item in order.items
            ],
        }

    if name == "detail_menu":
        menu = MenuService.get_by_id(int(args.get("menu_id", 0)))
        if not menu:
            return {"found": False, "message": "Menu tidak ditemukan."}
        return {
            "found": True,
            "id": menu.id,
            "name": menu.name,
            "description": menu.description,
            "price": menu.price,
            "category": menu.category,
            "rating": menu.rating,
            "is_best_seller": menu.is_best_seller,
        }

    return {"success": False, "error": f"Tool tidak dikenal: {name}"}


def _should_show_checkout(reply: str, session_id: str) -> bool:
    """
    Cek apakah reply model mengandung sinyal checkout DAN keranjang tidak kosong.
    Ini mencegah checkout terbuka saat keranjang masih kosong.
    """
    if not _CHECKOUT_SIGNALS.search(reply):
        return False
    summary = CartService.get_summary(session_id)
    return not summary.get("is_empty", True)


class ChatbotService:
    @staticmethod
    def chat(session_id: str, messages: list) -> dict:
        """
        messages: list of {"role": "user"|"assistant", "content": str}
        Return: {
            "reply": str,
            "history": list,
            "show_checkout": bool   # True = frontend tampilkan panel checkout
        }
        """
        api_key = current_app.config.get("GROQ_API_KEY")
        if not api_key:
            return {
                "reply": "Maaf, chatbot belum dikonfigurasi. Silakan hubungi admin.",
                "history": messages,
                "show_checkout": False,
            }

        client = Groq(api_key=api_key, timeout=20.0)
        model = current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile")

        # Pangkas history untuk hemat token, tapi tetap sertakan semua pesan
        # dalam konteks percakapan yang dikirim ke API
        trimmed = messages[-MAX_HISTORY:] if len(messages) > MAX_HISTORY else messages
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}] + trimmed

        try:
            for _ in range(MAX_TOOL_ITERATIONS):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=conversation,
                        tools=TOOLS,
                        tool_choice="auto",
                    )
                except BadRequestError:
                    response = client.chat.completions.create(
                        model=model,
                        messages=conversation,
                        tools=TOOLS,
                        tool_choice="none",
                    )

                msg = response.choices[0].message

                # Model tidak memanggil tool secara resmi
                if not msg.tool_calls:
                    reply = msg.content or ""

                    # Cek apakah model menulis tool call sebagai teks biasa
                    pseudo = _extract_pseudo_tool_call(reply)
                    if pseudo is not None:
                        func_name, args = pseudo
                        result = _execute_tool(func_name, args, session_id)
                        fake_id = f"call_pseudo_{func_name}"
                        conversation.append(
                            {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": fake_id,
                                        "type": "function",
                                        "function": {
                                            "name": func_name,
                                            "arguments": json.dumps(
                                                args, ensure_ascii=False
                                            ),
                                        },
                                    }
                                ],
                            }
                        )
                        conversation.append(
                            {
                                "role": "tool",
                                "tool_call_id": fake_id,
                                "name": func_name,
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )
                        continue  # lanjut iterasi supaya model bisa balas dengan hasil tool

                    # Balasan teks final
                    show_checkout = _should_show_checkout(reply, session_id)
                    messages.append({"role": "assistant", "content": reply})
                    return {
                        "reply": reply,
                        "history": messages,
                        "show_checkout": show_checkout,
                    }

                # Model memanggil satu atau lebih tool
                conversation.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}

                    result = _execute_tool(tc.function.name, args, session_id)
                    conversation.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.function.name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            # Melebihi MAX_TOOL_ITERATIONS
            reply = (
                "Maaf, permintaan kamu terlalu kompleks untuk saya proses sekarang. "
                "Coba lagi dengan pesan yang lebih sederhana."
            )
            messages.append({"role": "assistant", "content": reply})
            return {"reply": reply, "history": messages, "show_checkout": False}

        except Exception:
            current_app.logger.exception("ChatbotService.chat gagal")
            reply = (
                "Maaf, terjadi kendala saat menghubungi asisten. Coba lagi sebentar."
            )
            return {"reply": reply, "history": messages, "show_checkout": False}
