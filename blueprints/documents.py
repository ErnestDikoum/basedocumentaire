from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from models.models import db, Document, Categorie
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/')
def index():
    """Page d'accueil avec derniers documents"""
    try:
        categories = Categorie.query.order_by(Categorie.nom.asc()).all()
        derniers_documents = Document.query.order_by(Document.date_ajout.desc()).limit(8).all()
        
        # Statistiques globales
        stats = {
            'total_documents': Document.query.count(),
            'total_categories': Categorie.query.count()
        }
        
        return render_template(
            'index.html', 
            categories=categories, 
            documents=derniers_documents,
            stats=stats
        )
    except Exception as e:
        logger.error(f"Erreur dans index: {str(e)}")
        flash("Une erreur est survenue lors du chargement de la page.", 'error')
        return render_template('index.html', categories=[], documents=[], stats={})

@documents_bp.route('/categorie/<int:id>')
def show_category(id):
    """Affiche les documents d'une catégorie avec pagination et tri"""
    try:
        categorie = Categorie.query.get_or_404(id)
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('DOCUMENTS_PER_PAGE', 10)
        
        # Tri
        sort_by = request.args.get('sort', 'date_desc')
        
        query = Document.query.filter_by(categorie_id=id)
        
        # Appliquer le tri
        if sort_by == 'date_desc':
            query = query.order_by(Document.date_ajout.desc())
        elif sort_by == 'date_asc':
            query = query.order_by(Document.date_ajout.asc())
        elif sort_by == 'titre_asc':
            query = query.order_by(Document.titre.asc())
        elif sort_by == 'titre_desc':
            query = query.order_by(Document.titre.desc())
        elif sort_by == 'vues_desc':
            query = query.order_by(Document.nombre_vues.desc())
        
        # Paginer
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        documents = pagination.items
        
        return render_template(
            'categorie.html', 
            categorie=categorie, 
            documents=documents,
            pagination=pagination,
            sort_by=sort_by
        )
    except Exception as e:
        logger.error(f"Erreur dans show_category: {str(e)}")
        flash("Catégorie introuvable.", 'error')
        return redirect(url_for('documents.index'))

@documents_bp.route('/document/<int:id>')
def show_document(id):
    """Affiche les détails d'un document"""
    try:
        document = Document.query.get_or_404(id)
        
        # Incrémenter le compteur de vues
        document.increment_vues()
        
        # Documents similaires (même catégorie)
        documents_similaires = Document.query.filter(
            Document.categorie_id == document.categorie_id,
            Document.id != document.id
        ).order_by(Document.date_ajout.desc()).limit(5).all()
        
        return render_template(
            'document_detail.html',
            document=document,
            documents_similaires=documents_similaires
        )
    except Exception as e:
        logger.error(f"Erreur dans show_document: {str(e)}")
        flash("Document introuvable.", 'error')
        return redirect(url_for('documents.index'))

@documents_bp.route('/search')
def search():
    """Recherche avancée de documents"""
    query = request.args.get('q', '').strip()
    categorie_id = request.args.get('categorie', None)
    date_debut = request.args.get('date_debut', None)
    date_fin = request.args.get('date_fin', None)
    sort_by = request.args.get('sort', 'date_desc')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('DOCUMENTS_PER_PAGE', 10)
    
    if not query and not categorie_id and not date_debut:
        flash("Veuillez entrer au moins un critère de recherche.", 'warning')
        return redirect(url_for('documents.index'))
    
    try:
        # Construction de la requête
        search_query = Document.query
        
        # Filtre par terme de recherche
        if query:
            search_query = search_query.filter(
                db.or_(
                    Document.titre.ilike(f'%{query}%'),
                    Document.description.ilike(f'%{query}%')
                )
            )
        
        # Filtre par catégorie
        if categorie_id:
            search_query = search_query.filter_by(categorie_id=int(categorie_id))
        
        # Filtre par date
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d')
                search_query = search_query.filter(Document.date_ajout >= date_debut_obj)
            except ValueError:
                flash("Format de date de début invalide.", 'warning')
        
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d')
                search_query = search_query.filter(Document.date_ajout <= date_fin_obj)
            except ValueError:
                flash("Format de date de fin invalide.", 'warning')
        
        # Tri
        if sort_by == 'date_desc':
            search_query = search_query.order_by(Document.date_ajout.desc())
        elif sort_by == 'date_asc':
            search_query = search_query.order_by(Document.date_ajout.asc())
        elif sort_by == 'titre_asc':
            search_query = search_query.order_by(Document.titre.asc())
        elif sort_by == 'titre_desc':
            search_query = search_query.order_by(Document.titre.desc())
        elif sort_by == 'vues_desc':
            search_query = search_query.order_by(Document.nombre_vues.desc())
        
        # Pagination
        pagination = search_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
        
        # Récupérer toutes les catégories pour le formulaire
        categories = Categorie.query.order_by(Categorie.nom.asc()).all()
        
        return render_template(
            'search.html',
            query=query,
            results=results,
            pagination=pagination,
            categories=categories,
            selected_categorie=int(categorie_id) if categorie_id else None,
            date_debut=date_debut,
            date_fin=date_fin,
            sort_by=sort_by
        )
        
    except Exception as e:
        logger.error(f"Erreur dans search: {str(e)}")
        flash("Une erreur est survenue lors de la recherche.", 'error')
        return redirect(url_for('documents.index'))

@documents_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """Télécharge un fichier"""
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            flash("Le fichier demandé n'existe pas.", 'error')
            return redirect(url_for('documents.index'))
        
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Erreur lors de l'accès au fichier {filename}: {str(e)}")
        flash("Erreur lors de l'accès au fichier.", 'error')
        return redirect(url_for('documents.index'))