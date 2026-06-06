# FARMABOL - Sistema de Inventarios y Ventas

Sistema académico desarrollado para Farmacias Bolivianas Unidas (FARMABOL), empresa nacional con 12 sucursales.

## Funcionalidades

- Login con roles:
  - ADMIN: gestión total de productos, ventas, stock y dashboard.
  - VENDEDOR: registrar ventas y consultar stock.
- CRUD completo de productos.
- Registro de ventas con descuento automático de stock.
- Dashboard con:
  - Productos con stock bajo menor a 5 unidades.
  - Total de ventas del día.
  - Actualización automática cada 5 segundos.
- Persistencia con SQLite.
- Mínimo 3 tablas: `User`, `Product`, `Sale`.
- Despliegue preparado para Render.
- Análisis estático preparado con Pylint.

## Usuarios de prueba

| Rol | Usuario | Contraseña |
|---|---|---|
| ADMIN | admin | admin123 |
| VENDEDOR | vendedor | venta123 |

## Instalación local

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Luego abrir:

```text
http://127.0.0.1:5000
```

## Ejecutar análisis estático

```bash
pylint app.py
```

Guardar evidencia:

```bash
pylint app.py > docs/reporte_pylint.txt
```

## Despliegue en Render

1. Subir este proyecto a GitHub.
2. Entrar a Render.
3. Crear un nuevo Web Service.
4. Conectar el repositorio de GitHub.
5. Usar:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. Abrir la URL pública generada por Render.

## Commits importantes de refactorización

Este proyecto ya incluye una historia de Git con 5 commits.
Los commits clave son:

- `Implementa productos ventas y dashboard inicial con logica duplicada`
- `Refactoriza permisos y calculos del dashboard en funciones reutilizables`

En GitHub se puede abrir la comparación entre esos commits para evidenciar el antes y después de la refactorización.
