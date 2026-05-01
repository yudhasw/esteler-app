from flask import Blueprint, jsonify, request, render_template, current_app
from models import Menu
from services.ai_recommender import get_ai_recommendation
import urllib.parse

buyer_bp = Blueprint('buyer', __name__)

@buyer_bp.route('/')
def home():
    menus = Menu.query.filter_by(is_available=True).all()
    return render_template('menu.html', menus=menus)

@buyer_bp.route('/api/menus')
def list_menus():
    category = request.args.get('category')
    query = Menu.query.filter_by(is_available=True)
    if category:
        query = query.filter_by(category=category)
    return jsonify([m.to_dict() for m in query.all()])

@buyer_bp.route('/api/menus/<int:menu_id>')
def menu_detail(menu_id):
    menu = Menu.query.get_or_404(menu_id)
    return jsonify(menu.to_dict())

@buyer_bp.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}
    preference = data.get('preference', '')
    menus = Menu.query.filter_by(is_available=True).all()
    result = get_ai_recommendation(menus, preference)
    rec_ids = result.get('recommendations', [])
    recommended = [m.to_dict() for m in menus if m.id in rec_ids]
    return jsonify({"menus": recommended, "reason": result.get('reason', '')})

@buyer_bp.route('/api/whatsapp/<int:menu_id>')
def whatsapp_link(menu_id):
    menu = Menu.query.get_or_404(menu_id)
    wa = menu.seller.whatsapp or current_app.config['WHATSAPP_NUMBER']
    text = f"Halo, saya mau pesan {menu.name} (Rp{menu.price:,})"
    url = f"https://wa.me/{wa}?text={urllib.parse.quote(text)}"
    return jsonify({"whatsapp_url": url})