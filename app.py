import os
from datetime import date, datetime, timedelta
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "farmabol-dev-secret")
database_url = os.environ.get("DATABASE_URL", "sqlite:///farmabol.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    laboratory = db.Column(db.String(100), nullable=False)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship("Product")
    user = db.relationship("User")


def seed_database():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password_hash=generate_password_hash("admin123"), role="ADMIN"))
    if not User.query.filter_by(username="vendedor").first():
        db.session.add(User(username="vendedor", password_hash=generate_password_hash("venta123"), role="VENDEDOR"))
    if Product.query.count() == 0:
        db.session.add_all([
            Product(code="MED001", name="Paracetamol 500mg", price=2.50, stock=12, laboratory="INTI"),
            Product(code="MED002", name="Ibuprofeno 400mg", price=3.00, stock=4, laboratory="Bago"),
            Product(code="MED003", name="Amoxicilina 500mg", price=8.50, stock=8, laboratory="COFAR"),
            Product(code="MED004", name="Loratadina 10mg", price=1.80, stock=3, laboratory="Vita"),
        ])
    db.session.commit()


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user_id"] = user.id
            session["role"] = user.role
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)
    low_stock = Product.query.filter(Product.stock < 5).order_by(Product.stock.asc()).all()
    total_today = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(
        Sale.created_at >= today_start,
        Sale.created_at < today_end
    ).scalar()
    return render_template("dashboard.html", low_stock=low_stock, total_today=total_today)


@app.route("/api/dashboard")
def api_dashboard():
    if "user_id" not in session:
        return jsonify({"error": "no autorizado"}), 401
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)
    low_stock = Product.query.filter(Product.stock < 5).order_by(Product.stock.asc()).all()
    total_today = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(
        Sale.created_at >= today_start,
        Sale.created_at < today_end
    ).scalar()
    return jsonify({
        "total_today": round(total_today, 2),
        "low_stock": [{"code": item.code, "name": item.name, "stock": item.stock} for item in low_stock],
    })


@app.route("/productos")
def products():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "ADMIN":
        flash("Solo ADMIN puede gestionar productos.", "danger")
        return redirect(url_for("dashboard"))
    items = Product.query.order_by(Product.name).all()
    return render_template("products.html", products=items)


@app.route("/productos/nuevo", methods=["GET", "POST"])
def new_product():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "ADMIN":
        flash("Solo ADMIN puede crear productos.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        db.session.add(Product(
            code=request.form["code"],
            name=request.form["name"],
            price=float(request.form["price"]),
            stock=int(request.form["stock"]),
            laboratory=request.form["laboratory"],
        ))
        db.session.commit()
        flash("Producto creado correctamente.", "success")
        return redirect(url_for("products"))
    return render_template("product_form.html", product=None)


@app.route("/ventas", methods=["GET", "POST"])
def sales():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") not in ["ADMIN", "VENDEDOR"]:
        flash("No tiene permisos para registrar ventas.", "danger")
        return redirect(url_for("dashboard"))
    products_list = Product.query.order_by(Product.name).all()
    if request.method == "POST":
        product = Product.query.get_or_404(int(request.form["product_id"]))
        quantity = int(request.form["quantity"])
        if quantity <= 0:
            flash("La cantidad debe ser mayor a cero.", "danger")
        elif product.stock < quantity:
            flash("Stock insuficiente para realizar la venta.", "danger")
        else:
            total = product.price * quantity
            product.stock -= quantity
            db.session.add(Sale(product_id=product.id, user_id=session["user_id"], quantity=quantity, total=total))
            db.session.commit()
            flash("Venta registrada y stock actualizado.", "success")
            return redirect(url_for("dashboard"))
    return render_template("sales.html", products=products_list)


with app.app_context():
    seed_database()


if __name__ == "__main__":
    app.run(debug=True)
