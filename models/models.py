from flask_sqlalchemy import SQLAlchemy
import bcrypt
from datetime import datetime
import os

db = SQLAlchemy()

class Categorie(db.Model):
    """Modèle pour les catégories de documents"""
    __tablename__ = 'categorie'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Categorie {self.nom}>'
    
    @property
    def nb_documents(self):
        """Compte le nombre de documents dans cette catégorie"""
        return self.documents.count()
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'nom': self.nom,
            'description': self.description,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'nb_documents': self.nb_documents
        }

class Configuration(db.Model):
    """Modèle pour les configurations système"""
    __tablename__ = 'configuration'
    
    id = db.Column(db.Integer, primary_key=True)
    cle = db.Column(db.String(50), unique=True, nullable=False)
    valeur = db.Column(db.Text)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Configuration {self.cle}>'
    
    @staticmethod
    def get_value(cle, default=None):
        """Récupère une valeur de configuration"""
        config = Configuration.query.filter_by(cle=cle).first()
        return config.valeur if config else default
    
    @staticmethod
    def set_value(cle, valeur):
        """Définit une valeur de configuration"""
        config = Configuration.query.filter_by(cle=cle).first()
        if config:
            config.valeur = valeur
        else:
            config = Configuration(cle=cle, valeur=valeur)
            db.session.add(config)
        db.session.commit()

class Document(db.Model):
    """Modèle pour les documents"""
    __tablename__ = 'document'
    
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    fichier_nom = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=False)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    taille_fichier = db.Column(db.Integer)  # En octets
    nombre_vues = db.Column(db.Integer, default=0)
    
    # Relation avec Categorie
    categorie = db.relationship('Categorie', backref=db.backref('documents', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Document {self.titre}>'
    
    def increment_vues(self):
        """Incrémente le compteur de vues"""
        self.nombre_vues += 1
        db.session.commit()
    
    def get_extension(self):
        """Retourne l'extension du fichier"""
        return os.path.splitext(self.fichier_nom)[1].lower()
    
    def get_taille_lisible(self):
        """Retourne la taille du fichier en format lisible"""
        if not self.taille_fichier:
            return "Inconnue"
        
        size = float(self.taille_fichier)
        for unit in ['o', 'Ko', 'Mo', 'Go', 'To']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} To"
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'titre': self.titre,
            'fichier_nom': self.fichier_nom,
            'description': self.description,
            'categorie_id': self.categorie_id,
            'categorie_nom': self.categorie.nom if self.categorie else None,
            'date_ajout': self.date_ajout.isoformat() if self.date_ajout else None,
            'date_modification': self.date_modification.isoformat() if self.date_modification else None,
            'taille_fichier': self.taille_fichier,
            'nombre_vues': self.nombre_vues
        }

class User(db.Model):
    """Modèle utilisateur"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash le mot de passe avec bcrypt"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password):
        """Vérifie le mot de passe"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )
    
    def update_derniere_connexion(self):
        """Met à jour la date de dernière connexion"""
        self.derniere_connexion = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'date_creation': self.date_creation.isoformat() if self.date_creation else None,
            'derniere_connexion': self.derniere_connexion.isoformat() if self.derniere_connexion else None
        }