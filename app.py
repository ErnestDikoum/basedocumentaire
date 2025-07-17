# app.py
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from functools import wraps
from flask import session
import os
from functools import wraps


app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Models
class Categorie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    fichier_nom = db.Column(db.String(200), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=False)
    categorie = db.relationship('Categorie', backref=db.backref('documents', lazy=True))

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple authentication check (replace with real authentication logic)
        if username == 'admin' and password == 'password':
            session['is_admin'] = True
            session['username'] = username
            flash('Connexion réussie.')
            return redirect(url_for('index'))
        else:
            flash('Identifiants incorrects.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Déconnexion réussie.')
    return redirect(url_for('index'))



@app.route('/')
def index():
    categories = Categorie.query.all()
    derniers_documents = Document.query.order_by(Document.id.desc()).limit(5).all()
    return render_template('index.html', categories=categories, documents=derniers_documents)


@app.route('/categorie/<int:id>')
def show_category(id):
    categorie = Categorie.query.get_or_404(id)
    documents = Document.query.filter_by(categorie_id=id).all()
    return render_template('categorie.html', categorie=categorie, documents=documents)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
        flash("Le fichier demandé n'existe pas.")
        return redirect(url_for('index'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin')
def admin():
    categories = Categorie.query.all()
    documents = Document.query.all() 
    
    if not session.get('is_admin'):
        flash("Vous devez être connecté en tant qu'administrateur pour accéder à cette page.")
        return redirect(url_for('login'))
    return render_template('admin.html', categories=categories, documents=documents)


@app.route('/admin/add-category', methods=['POST'])
def add_category():
    nom = request.form['nom']
    description = request.form.get('description', '')

    if nom.strip():
        new_cat = Categorie(nom=nom.strip(), description=description.strip())
        db.session.add(new_cat)
        db.session.commit()
        flash("Catégorie ajoutée avec succès.")
    else:
        flash("Le nom de la catégorie est requis.")

    return redirect(url_for('admin'))

@app.route('/admin/edit-category/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    cat = Categorie.query.get_or_404(id)

    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form.get('description', '')

        if nom.strip():
            cat.nom = nom.strip()
            cat.description = description.strip()
            db.session.commit()
            flash('Catégorie mise à jour avec succès.')
        else:
            flash("Le nom de la catégorie est requis.")

        return redirect(url_for('admin'))

    return render_template('edit_category.html', category=cat)

@app.route('/admin/delete-category/<int:id>', methods=['POST'])
def delete_category(id):                                                                                                                                                                                                                                        
    cat = Categorie.query.get_or_404(id)

    # Supprimer tous les documents associés
    for doc in cat.documents:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc.fichier_nom)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(doc)

    # Supprimer la catégorie
    db.session.delete(cat)
    db.session.commit()
    flash('Catégorie supprimée avec succès.')
    return redirect(url_for('admin'))

@app.route('/admin/add-document', methods=['POST'])
def add_document():
    titre = request.form['titre']
    categorie_id = request.form['categorie_id']
    files = request.files.getlist('files[]')

    if not files:
        flash("Aucun fichier n'a été sélectionné.")
        return redirect(url_for('admin'))

    for file in files:
        if file and file.filename.endswith(('.pdf', '.doc', '.docx')):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            doc = Document(
                titre=f"{titre} - {filename}",
                fichier_nom=filename,
                categorie_id=categorie_id
            )
            db.session.add(doc)
        db.session.commit()
        flash('Document ajouté avec succès.')
   

    return redirect(url_for('admin'))


@app.route('/admin/edit-document/<int:id>', methods=['GET', 'POST'])
def edit_document(id):
    doc = Document.query.get_or_404(id)

    if request.method == 'POST':
        titre = request.form['titre']
        categorie_id = request.form['categorie_id']
        file = request.files.get('file')

        if titre.strip():
            doc.titre = titre.strip()
            doc.categorie_id = categorie_id

            if file and file.filename.endswith(('.pdf', '.doc', '.docx')):
                # Supprimer l'ancien fichier
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc.fichier_nom)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)

                # Enregistrer le nouveau fichier
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                doc.fichier_nom = filename

            db.session.commit()
            flash('Document mis à jour avec succès.')
        else:
            flash("Le titre du document est requis.")

        return redirect(url_for('admin'))

    categories = Categorie.query.all()
    return render_template('edit_document.html', document=doc, categories=categories)


@app.route('/admin/delete-document/<int:id>', methods=['POST'])
def delete_document(id):
    doc = Document.query.get_or_404(id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc.fichier_nom)

    # Supprimer le fichier du disque
    if os.path.exists(filepath):
        os.remove(filepath)

    # Supprimer le document de la base
    db.session.delete(doc)
    db.session.commit()
    flash('Document supprimé.')
    return redirect(url_for('admin'))


@app.route('/reset-db', methods=['POST'])
def reset_db():
    db.drop_all()
    db.create_all()
    db.session.commit()
    flash('Base de données réinitialisée.')
    return redirect(url_for('admin'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()

    if not query:
        flash("Veuillez entrer un terme de recherche.")
        return redirect(url_for('index'))

    results = Document.query.filter(Document.titre.ilike(f'%{query}%')).all()

    return render_template('search.html', query=query, results=results)

# Décorateur pour vérifier si l'utilisateur est connecté en tant qu'administrateur
def login_required_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Vous devez être connecté en tant qu'administrateur pour accéder à cette page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Exécution
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('database.db'):
            db.create_all()
            db.session.commit()
    app.run(debug=True)
    
