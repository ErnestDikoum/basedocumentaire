from flask import Flask, render_template, session
from flask_wtf.csrf import CSRFProtect
import os
import logging
from config import Config

# Initialisation du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Factory pour créer l'application Flask"""
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialiser la configuration
    config_class.init_app(app)
    
    # Initialiser les extensions
    csrf = CSRFProtect(app)
    
    # Importer et initialiser la base de données
    from models.models import db
    db.init_app(app)
    
    # Créer les tables si nécessaire
    with app.app_context():
        db.create_all()
        logger.info("Base de données initialisée")
    
    # Enregistrer les blueprints
    from blueprints.auth import auth_bp
    from blueprints.documents import documents_bp
    from blueprints.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp)
    
    logger.info("Blueprints enregistrés")
    
    # Gestionnaires d'erreurs
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Erreur 500: {str(e)}")
        from models.models import db
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large(e):
        from flask import flash, redirect, url_for
        flash("Le fichier est trop volumineux. Taille maximale: 100 MB", 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Context processor pour injecter des variables dans tous les templates
    @app.context_processor
    def inject_user():
        """Injecte les infos utilisateur dans tous les templates"""
        return {
            'is_admin': session.get('is_admin', False),
            'username': session.get('username', None),
            'user_id': session.get('user_id', None)
        }
    
    @app.context_processor
    def inject_config():
        """Injecte des variables de config utiles"""
        return {
            'app_name': 'Base Documentaire Numérique Agriculture',
            'year': 2024
        }
    
    @app.context_processor
    def inject_announcement():
        """Injecte le message défilant et le dernier document"""
        try:
            from models.models import Document, Configuration
            # Dernier document ajouté
            dernier_doc = Document.query.order_by(Document.id.desc()).first()
            
            # Message personnalisé
            config_message = Configuration.get_value('message_defilant')
            
            return dict(dernier_doc=dernier_doc, config_message=config_message)
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'annonce: {e}")
            return dict(dernier_doc=None, config_message=None)
    
    # Commandes CLI personnalisées
    @app.cli.command()
    def init_db():
        """Initialise la base de données"""
        from models.models import db
        db.create_all()
        logger.info("Base de données initialisée via CLI")
        print("✅ Base de données initialisée avec succès")
    
    @app.cli.command()
    def create_admin():
        """Crée un utilisateur admin via CLI"""
        from models.models import db, User
        import getpass
        
        username = input("Nom d'utilisateur: ")
        email = input("Email (optionnel): ")
        password = getpass.getpass("Mot de passe: ")
        password_confirm = getpass.getpass("Confirmez le mot de passe: ")
        
        if password != password_confirm:
            print("❌ Les mots de passe ne correspondent pas")
            return
        
        try:
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"❌ L'utilisateur '{username}' existe déjà")
                return
            
            user = User(username=username, email=email if email else None, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"✅ Utilisateur admin '{username}' créé avec succès")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur: {str(e)}")
    
    @app.cli.command()
    def seed_data():
        """Ajoute des données de test"""
        from models.models import db, Categorie
        
        try:
            categories_test = [
                {"nom": "Agriculture de précision", "description": "Technologies et techniques pour optimiser les rendements"},
                {"nom": "Irrigation intelligente", "description": "Systèmes d'irrigation automatisés et connectés"},
                {"nom": "Capteurs et IoT", "description": "Capteurs agricoles et objets connectés"},
                {"nom": "Drones agricoles", "description": "Utilisation de drones pour l'agriculture"},
                {"nom": "Data Analytics", "description": "Analyse de données pour l'agriculture"}
            ]
            
            for cat_data in categories_test:
                existing = Categorie.query.filter_by(nom=cat_data['nom']).first()
                if not existing:
                    cat = Categorie(**cat_data)
                    db.session.add(cat)
            
            db.session.commit()
            print("✅ Données de test ajoutées avec succès")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur: {str(e)}")
    
    logger.info("Application Flask créée avec succès")
    return app

# Créer l'application
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=app.config.get('FLASK_DEBUG', True),
        host='0.0.0.0',
        port=5000
    )