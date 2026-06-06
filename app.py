"""Sistema FARMABOL: inventario y ventas para evaluación práctica."""

import os
from datetime import date, datetime, timedelta
from functools import wraps

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
    """Usuario del sistema con rol ADMIN o VENDEDOR."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)


class Product(db.Model):
    """Producto farmacéutico disponible para venta."""

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    laboratory = db.Column(db.String(100), nullable=False)


class Sale(db.Model):
    """Venta registrada por un usuario."""

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship("Product")
    user = db.relationship("User")


def login_required(view_function):
    """Evita que usuarios no autenticados entren a rutas privadas."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Debe iniciar sesión para continuar.", "warning")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def roles_required(*allowed_roles):
    """Valida permisos según el rol almacenado en sesión."""

    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            if session.get("role") not in allowed_roles:
                flash("No tiene permisos para realizar esta acción.", "danger")
                return redirect(url_for("dashboard"))
            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator


def get_dashboard_metrics():
    """Obtiene métricas usadas por el dashboard y por la API en tiempo real."""

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    low_stock = Product.query.filter(Product.stock < 5).order_by(Product.stock.asc()).all()
    total_today = db.session.query(func.coalesce(func.sum(Sale.total), 0)).filter(
        Sale.created_at >= today_start,
        Sale.created_at < today_end,
    ).scalar()

    return low_stock, float(total_today)


def create_sale(product_id, quantity, user_id):
    """Registra una venta y descuenta stock de forma centralizada."""

    product = Product.query.get_or_404(product_id)

    if quantity <= 0:
        raise ValueError("La cantidad debe ser mayor a cero.")

    if product.stock < quantity:
        raise ValueError("Stock insuficiente para realizar la venta.")

    total = product.price * quantity
    product.stock -= quantity

    sale = Sale(product_id=product.id, user_id=user_id, quantity=quantity, total=total)
    db.session.add(sale)
    db.session.commit()

    return sale


def seed_database():
    """Crea tablas y datos iniciales para probar el sistema."""

    db.create_all()

    if not User.query.filter_by(username="admin").first():
        db.session.add(
            User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                role="ADMIN",
            )
        )

    if not User.query.filter_by(username="vendedor").first():
        db.session.add(
            User(
                username="vendedor",
                password_hash=generate_password_hash("venta123"),
                role="VENDEDOR",
            )
        )

    if Product.query.count() == 0:
        db.session.add_all(
            [
                Product(code="MED001", name="Paracetamol 500mg", price=2.50, stock=12, laboratory="INTI"),
                Product(code="MED002", name="Ibuprofeno 400mg", price=3.00, stock=4, laboratory="Bago"),
                Product(code="MED003", name="Amoxicilina 500mg", price=8.50, stock=8, laboratory="COFAR"),
                Product(code="MED004", name="Loratadina 10mg", price=1.80, stock=3, laboratory="Vita"),
                Product(code="MED005", name="Omeprazol 20mg", price=2.20, stock=15, laboratory="COFAR"),
            ]
        )

    db.session.commit()


@app.route("/")
def index():
    """Redirige al login como pantalla inicial."""

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Autentica a los usuarios del sistema."""

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
    """Cierra la sesión activa."""

    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Muestra productos con bajo stock y ventas del día."""

    low_stock, total_today = get_dashboard_metrics()
    return render_template("dashboard.html", low_stock=low_stock, total_today=total_today)


@app.route("/api/dashboard")
@login_required
def api_dashboard():
    """Entrega métricas en JSON para actualización en tiempo real."""

    low_stock, total_today = get_dashboard_metrics()
    return jsonify(
        {
            "total_today": round(total_today, 2),
            "low_stock": [
                {"code": item.code, "name": item.name, "stock": item.stock}
                for item in low_stock
            ],
        }
    )


@app.route("/productos")
@login_required
@roles_required("ADMIN")
def products():
    """Lista productos para administración."""

    items = Product.query.order_by(Product.name).all()
    return render_template("products.html", products=items)


@app.route("/stock")
@login_required
@roles_required("ADMIN", "VENDEDOR")
def stock():
    """Permite consultar stock sin modificar productos."""

    items = Product.query.order_by(Product.name).all()
    return render_template("stock.html", products=items)


@app.route("/productos/nuevo", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def new_product():
    """Crea un producto nuevo."""

    if request.method == "POST":
        product = Product(
            code=request.form["code"].strip().upper(),
            name=request.form["name"].strip(),
            price=float(request.form["price"]),
            stock=int(request.form["stock"]),
            laboratory=request.form["laboratory"].strip(),
        )
        db.session.add(product)
        db.session.commit()

        flash("Producto creado correctamente.", "success")
        return redirect(url_for("products"))

    return render_template("product_form.html", product=None)


@app.route("/productos/<int:product_id>/editar", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def edit_product(product_id):
    """Edita un producto existente."""

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.code = request.form["code"].strip().upper()
        product.name = request.form["name"].strip()
        product.price = float(request.form["price"])
        product.stock = int(request.form["stock"])
        product.laboratory = request.form["laboratory"].strip()
        db.session.commit()

        flash("Producto actualizado correctamente.", "success")
        return redirect(url_for("products"))

    return render_template("product_form.html", product=product)


@app.route("/productos/<int:product_id>/eliminar", methods=["POST"])
@login_required
@roles_required("ADMIN")
def delete_product(product_id):
    """Elimina un producto si no tiene ventas asociadas."""

    product = Product.query.get_or_404(product_id)

    if Sale.query.filter_by(product_id=product.id).first():
        flash("No se puede eliminar porque el producto ya tiene ventas.", "warning")
    else:
        db.session.delete(product)
        db.session.commit()
        flash("Producto eliminado correctamente.", "success")

    return redirect(url_for("products"))


@app.route("/ventas", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "VENDEDOR")
def sales():
    """Registra ventas y descuenta stock automáticamente."""

    products_list = Product.query.order_by(Product.name).all()

    if request.method == "POST":
        try:
            create_sale(
                product_id=int(request.form["product_id"]),
                quantity=int(request.form["quantity"]),
                user_id=session["user_id"],
            )
            flash("Venta registrada y stock actualizado.", "success")
            return redirect(url_for("dashboard"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("sales.html", products=products_list)


with app.app_context():
    seed_database()


if __name__ == "__main__":
    app.run(debug=True)
