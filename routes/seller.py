from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from models import db, Menu

seller_bp = Blueprint('seller', __name__, url_prefix='/seller')

@seller_bp.route('/dashboard')
@login_required
def dashboard():
    menus = Menu.query.filter_by(seller_id=current_user.id).all()
    return render_template('dashboard.html', menus=menus)

@seller_bp.route('/api/menus', methods=['GET', 'POST'])
@login_required
def manage_menus():
    if request.method == 'POST':
        data = request.get_json()
        menu = Menu(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            category=data.get('category'),
            image_url=data.get('image_url'),
            seller_id=current_user.id
        )
        db.session.add(menu)
        db.session.commit()
        return jsonify(menu.to_dict()), 201
    menus = Menu.query.filter_by(seller_id=current_user.id).all()
    return jsonify([m.to_dict() for m in menus])

@seller_bp.route('/api/menus/<int:menu_id>', methods=['PUT', 'DELETE'])
@login_required
def edit_menu(menu_id):
    menu = Menu.query.filter_by(id=menu_id, seller_id=current_user.id).first_or_404()
    if request.method == 'DELETE':
        db.session.delete(menu)
        db.session.commit()
        return jsonify({"message": "Dihapus"})
    data = request.get_json()
    for field in ['name', 'description', 'price', 'category', 'image_url', 'is_available']:
        if field in data:
            setattr(menu, field, data[field])
    db.session.commit()
    return jsonify(menu.to_dict())

@seller_bp.route('/api/menus/<int:menu_id>/bestseller', methods=['POST'])
@login_required
def toggle_bestseller(menu_id):
    menu = Menu.query.filter_by(id=menu_id, seller_id=current_user.id).first_or_404()
    menu.is_bestseller = not menu.is_bestseller
    db.session.commit()
    return jsonify(menu.to_dict())