from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from models.models import db, User
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'warning')
            return render_template('auth/login.html')
        
        # Vérifier d'abord dans la base de données
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['is_admin'] = user.is_admin
            session['username'] = user.username
            session['user_id'] = user.id
            
            # Mettre à jour la dernière connexion
            user.update_derniere_connexion()
            
            logger.info(f"Connexion réussie pour l'utilisateur: {username}")
            flash('Connexion réussie.', 'success')
            
            # Rediriger vers la page demandée ou vers l'accueil
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('documents.index'))
        
        # Fallback sur l'authentification de configuration (temporaire)
        elif username == current_app.config['ADMIN_USERNAME'] and password == current_app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            session['username'] = username
            logger.warning(f"Connexion avec credentials de configuration: {username}")
            flash('Connexion réussie. Pensez à créer un compte utilisateur sécurisé.', 'info')
            return redirect(url_for('documents.index'))
        else:
            logger.warning(f"Tentative de connexion échouée pour: {username}")
            flash('Identifiants incorrects.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Déconnexion de l'utilisateur"""
    username = session.get('username', 'Inconnu')
    session.clear()
    logger.info(f"Déconnexion de l'utilisateur: {username}")
    flash('Déconnexion réussie.', 'success')
    return redirect(url_for('documents.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription (désactivée par défaut, à activer si besoin)"""
    # Pour l'instant, on désactive l'auto-inscription
    # Seuls les admins peuvent créer des comptes
    flash("L'inscription publique est désactivée. Contactez un administrateur.", 'info')
    return redirect(url_for('auth.login'))