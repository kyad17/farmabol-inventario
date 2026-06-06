# Arquitectura del sistema FARMABOL

Se eligió una arquitectura monolítica por capas porque el sistema es pequeño, académico y debe entregarse rápidamente.
La aplicación concentra frontend, backend y persistencia en un mismo proyecto Flask, pero separa responsabilidades:

- Presentación: plantillas HTML con Bootstrap.
- Controlador: rutas de Flask.
- Lógica de negocio: funciones como `create_sale` y `get_dashboard_metrics`.
- Persistencia: modelos SQLAlchemy y base de datos SQLite.

## Diagrama simple

Usuario ADMIN/VENDEDOR
        ↓
Interfaz Web HTML + Bootstrap
        ↓
Rutas Flask / Controladores
        ↓
Lógica de negocio
        ↓
Modelos SQLAlchemy
        ↓
Base de datos SQLite

## Tablas mínimas
- User: usuarios y roles.
- Product: productos farmacéuticos.
- Sale: ventas registradas.
