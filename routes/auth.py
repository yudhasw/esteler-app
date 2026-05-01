from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_user, logout_user, login_required
from models import Seller

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        seller = Seller.query.filter_by(username=username).first()
        if seller and seller.check_password(password):
            login_user(seller)
            if request.is_json:
                return jsonify({"message": "Login berhasil", "shop": seller.shop_name})
            return redirect(url_for('seller.dashboard'))
        return jsonify({"error": "Username/password salah"}), 401
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('buyer.home'))