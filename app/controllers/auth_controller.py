from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from app.models.user import USERS_DB

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        return redirect(url_for('ticket.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = USERS_DB.get(username)
        
        if not user or not user.check_password(password):
            flash("Credenciales inválidas.", "error")
            return render_template('login.html'), 401
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        
        return redirect(url_for('ticket.dashboard'))
        
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for('auth.login'))
