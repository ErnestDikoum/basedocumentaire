from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from models.models import db, Document, Categorie, User, Configuration
from werkzeug.utils import secure_filename
from functools import wraps
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==================== DECORATEUR ====================
def login_required_admin(f):
    """Décorateur pour protéger les routes admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Vous devez être connecté en tant qu'administrateur pour accéder à cette page.", 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== FONCTIONS UTILITAIRES ====================
def allowed_file(filename):
    """Vérifie si l'extension du fichier est autorisée"""
    return os.path.splitext(filename)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_unique_filename(filename):
    """Génère un nom de fichier unique pour éviter les conflits"""
    filename = secure_filename(filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return filename
    
    base, ext = os.path.splitext(filename)
    counter = 1
    
    while os.path.exists(filepath):
        filename = f"{base}_{counter}{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        counter += 1
    
    return filename

def delete_file_safe(filename):
    """Supprime un fichier de manière sécurisée"""
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Fichier supprimé: {filename}")
            return True
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du fichier {filename}: {str(e)}")
    return False

def get_file_size(filepath):
    """Retourne la taille d'un fichier en octets"""
    try:
        if os.path.exists(filepath):
            return os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la taille: {str(e)}")
    return None

# ==================== DASHBOARD ====================
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required_admin
def dashboard():
    """Dashboard administrateur avec statistiques"""
    try:
        categories = Categorie.query.order_by(Categorie.nom.asc()).all()
        documents = Document.query.order_by(Document.date_ajout.desc()).limit(10).all()
        users = User.query.all()
        
        # Statistiques avancées
        date_limite = datetime.utcnow() - timedelta(days=7)
        documents_recents = Document.query.filter(Document.date_ajout >= date_limite).count()
        
        # Top 5 documents les plus vus
        top_documents = Document.query.order_by(Document.nombre_vues.desc()).limit(5).all()
        
        stats = {
            'total_categories': len(categories),
            'total_documents': Document.query.count(),
            'total_users': len(users),
            'documents_recents': documents_recents,
            'top_documents': top_documents
        }
        
        return render_template('admin.html', 
                             categories=categories, 
                             documents=documents, 
                             users=users,
                             stats=stats)
    except Exception as e:
        logger.error(f"Erreur dans dashboard: {str(e)}")
        flash("Une erreur est survenue.", 'error')
        return redirect(url_for('documents.index'))

# ==================== GESTION DES CATEGORIES ====================
@admin_bp.route('/add-category', methods=['POST'])
@login_required_admin
def add_category():
    """Ajoute une nouvelle catégorie"""
    nom = request.form.get('nom', '').strip()
    description = request.form.get('description', '').strip()
    
    if not nom:
        flash("Le nom de la catégorie est requis.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    try:
        # Vérifier si la catégorie existe déjà
        existing = Categorie.query.filter_by(nom=nom).first()
        if existing:
            flash(f"Une catégorie '{nom}' existe déjà.", 'warning')
            return redirect(url_for('admin.dashboard'))
        
        new_cat = Categorie(nom=nom, description=description)
        db.session.add(new_cat)
        db.session.commit()
        logger.info(f"Catégorie ajoutée: {nom}")
        flash("Catégorie ajoutée avec succès.", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'ajout de la catégorie: {str(e)}")
        flash("Erreur lors de l'ajout de la catégorie.", 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit-category/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_category(id):
    """Modifie une catégorie"""
    cat = Categorie.query.get_or_404(id)
    
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        description = request.form.get('description', '').strip()
        
        if not nom:
            flash("Le nom de la catégorie est requis.", 'warning')
            return render_template('edit_category.html', category=cat)
        
        try:
            cat.nom = nom
            cat.description = description
            db.session.commit()
            logger.info(f"Catégorie modifiée: {nom}")
            flash('Catégorie mise à jour avec succès.', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification de la catégorie: {str(e)}")
            flash("Erreur lors de la modification.", 'error')
    
    return render_template('edit_category.html', category=cat)

@admin_bp.route('/delete-category/<int:id>', methods=['POST'])
@login_required_admin
def delete_category(id):
    """Supprime une catégorie et tous ses documents"""
    try:
        cat = Categorie.query.get_or_404(id)
        
        # Supprimer les fichiers associés
        for doc in cat.documents:
            delete_file_safe(doc.fichier_nom)
        
        # La cascade s'occupe de supprimer les documents
        db.session.delete(cat)
        db.session.commit()
        logger.info(f"Catégorie supprimée: {cat.nom}")
        flash('Catégorie supprimée avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de la catégorie: {str(e)}")
        flash("Erreur lors de la suppression.", 'error')
    
    return redirect(url_for('admin.dashboard'))

# ==================== GESTION DES DOCUMENTS ====================
@admin_bp.route('/add-document', methods=['POST'])
@login_required_admin
def add_document():
    """Ajoute un ou plusieurs documents"""
    titre = request.form.get('titre', '').strip()
    description = request.form.get('description', '').strip()
    categorie_id = request.form.get('categorie_id')
    files = request.files.getlist('files[]')
    
    if not titre:
        flash("Le titre est requis.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    if not categorie_id:
        flash("Veuillez sélectionner une catégorie.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    if not files or files[0].filename == '':
        flash("Aucun fichier n'a été sélectionné.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    success_count = 0
    error_count = 0
    
    try:
        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    logger.warning(f"Extension non autorisée: {file.filename}")
                    error_count += 1
                    continue
                
                filename = get_unique_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                
                file.save(filepath)
                
                # Récupérer la taille du fichier
                taille = get_file_size(filepath)
                
                doc = Document(
                    titre=f"{titre} - {filename}" if len(files) > 1 else titre,
                    description=description,
                    fichier_nom=filename,
                    categorie_id=categorie_id,
                    taille_fichier=taille
                )
                db.session.add(doc)
                success_count += 1
        
        db.session.commit()
        
        if success_count > 0:
            logger.info(f"{success_count} document(s) ajouté(s)")
            flash(f'{success_count} document(s) ajouté(s) avec succès.', 'success')
        if error_count > 0:
            flash(f'{error_count} fichier(s) rejeté(s) (extension non autorisée).', 'warning')
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'ajout de documents: {str(e)}")
        flash("Erreur lors de l'ajout des documents.", 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/edit-document/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_document(id):
    """Modifie un document"""
    doc = Document.query.get_or_404(id)
    
    if request.method == 'POST':
        titre = request.form.get('titre', '').strip()
        description = request.form.get('description', '').strip()
        categorie_id = request.form.get('categorie_id')
        file = request.files.get('file')
        
        if not titre:
            flash("Le titre du document est requis.", 'warning')
            return render_template('edit_document.html', document=doc, categories=Categorie.query.all())
        
        try:
            doc.titre = titre
            doc.description = description
            doc.categorie_id = categorie_id
            doc.date_modification = datetime.utcnow()
            
            # Si un nouveau fichier est uploadé
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash("Extension de fichier non autorisée.", 'warning')
                    return render_template('edit_document.html', document=doc, categories=Categorie.query.all())
                
                # Supprimer l'ancien fichier
                delete_file_safe(doc.fichier_nom)
                
                # Sauvegarder le nouveau
                filename = get_unique_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                doc.fichier_nom = filename
                doc.taille_fichier = get_file_size(filepath)
            
            db.session.commit()
            logger.info(f"Document modifié: {titre}")
            flash('Document mis à jour avec succès.', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur lors de la modification du document: {str(e)}")
            flash("Erreur lors de la modification.", 'error')
    
    categories = Categorie.query.all()
    return render_template('edit_document.html', document=doc, categories=categories)

@admin_bp.route('/delete-document/<int:id>', methods=['POST'])
@login_required_admin
def delete_document(id):
    """Supprime un document"""
    try:
        doc = Document.query.get_or_404(id)
        delete_file_safe(doc.fichier_nom)
        db.session.delete(doc)
        db.session.commit()
        logger.info(f"Document supprimé: {doc.titre}")
        flash('Document supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression du document: {str(e)}")
        flash("Erreur lors de la suppression.", 'error')
    
    return redirect(url_for('admin.dashboard'))

# ==================== GESTION DES CONFIGURATIONS ====================
@admin_bp.route('/update_announcement', methods=['POST'])
@login_required_admin
def update_announcement():
    """Met à jour le message défilant"""
    nouveau_message = request.form.get('custom_message', '').strip()
    
    try:
        Configuration.set_value('message_defilant', nouveau_message)
        logger.info(f"Message défilant mis à jour")
        flash("Le message défilant a été mis à jour avec succès!", 'success')
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du message: {str(e)}")
        flash("Erreur lors de la mise à jour du message.", 'error')
    
    return redirect(url_for('admin.dashboard'))

# ==================== GESTION DES UTILISATEURS ====================
@admin_bp.route('/create-admin-user', methods=['POST'])
@login_required_admin
def create_admin_user():
    """Crée un utilisateur admin"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == 'on'
    
    if not username or not password:
        flash("Nom d'utilisateur et mot de passe requis.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    try:
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f"L'utilisateur '{username}' existe déjà.", 'warning')
            return redirect(url_for('admin.dashboard'))
        
        user = User(username=username, email=email if email else None, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Utilisateur créé: {username} (Admin: {is_admin})")
        flash(f"Utilisateur '{username}' créé avec succès.", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
        flash("Erreur lors de la création de l'utilisateur.", 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete-user/<int:id>', methods=['POST'])
@login_required_admin
def delete_user(id):
    """Supprime un utilisateur"""
    try:
        user = User.query.get_or_404(id)
        
        # Empêcher la suppression de son propre compte
        if user.id == session.get('user_id'):
            flash("Vous ne pouvez pas supprimer votre propre compte.", 'warning')
            return redirect(url_for('admin.dashboard'))
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        logger.info(f"Utilisateur supprimé: {username}")
        flash(f"Utilisateur '{username}' supprimé avec succès.", 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
        flash("Erreur lors de la suppression.", 'error')
    
    return redirect(url_for('admin.dashboard'))

# ==================== UTILITAIRES ====================
@admin_bp.route('/reset-db', methods=['POST'])
@login_required_admin
def reset_db():
    """ATTENTION: Supprime toutes les données!"""
    confirmation = request.form.get('confirmation', '').strip()
    
    if confirmation != 'RESET':
        flash("Veuillez taper 'RESET' pour confirmer la réinitialisation.", 'warning')
        return redirect(url_for('admin.dashboard'))
    
    try:
        db.drop_all()
        db.create_all()
        db.session.commit()
        logger.warning("⚠️ Base de données réinitialisée!")
        flash('Base de données réinitialisée. Toutes les données ont été supprimées.', 'warning')
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation de la DB: {str(e)}")
        flash("Erreur lors de la réinitialisation.", 'error')
    
    return redirect(url_for('admin.dashboard'))