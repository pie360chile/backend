"""CRUD de páginas del portal público (CMS Página Web)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.backend.db.models import WebPageModel


DEFAULT_PAGES: list[dict[str, Any]] = [
    {
        "slug": "home",
        "title": "Inicio",
        "menu_label": "Inicio",
        "sort_order": 1,
        "content": {
            "hero_title_prefix": "Lleva tu",
            "hero_title_highlight": "Programa de Integración Escolar",
            "hero_title_suffix": "al siguiente nivel con",
            "hero_subtitle": "Gestión integral - Cumplimiento Normativo - Decisiones Basadas en Datos",
            "about_title": "Quiénes Somos",
            "about_p1": "En PIE 360 transformamos la gestión del Programa de Integración Escolar con una propuesta que une tecnología, experiencia y compromiso humano.",
            "about_p2": "Nuestra misión es acompañar a los colegios en la implementación de un sistema de inclusión eficiente, trazable y basado en datos reales.",
            "about_cta": "Ver más",
            "about_image": "/about_us.jpg",
            "what_we_do_title": "Qué Hacemos",
            "what_we_do_p1": "Diseñamos una plataforma integral que facilita el cumplimiento normativo y la gestión pedagógica del PIE, abordando los principales desafíos administrativos y técnicos de los establecimientos.",
            "what_we_do_p2": "Con PIE 360, los colegios optimizan tiempos administrativos, reducen burocracia y fortalecen las intervenciones pedagógicas, potenciando la colaboración de los equipos multidisciplinarios y el desarrollo integral de los estudiantes.",
            "what_we_do_cta": "Ver más",
            "what_we_do_image": "/what_we_do.jpg",
            "commitment_title": "Nuestro Compromiso",
            "commitment_p1": "PIE 360 es más que tecnología, es un ecosistema de innovación y apoyo experto que asegura excelencia, trazabilidad y cumplimiento normativo en cada etapa del proceso educativo.",
            "commitment_p2": "Conectamos personas, datos y buenas prácticas para hacer de la inclusión escolar una experiencia más efectiva, humana y sostenible.",
            "resources_title": "Recursos",
            "clients_title": "Nuestros Clientes",
        },
    },
    {
        "slug": "about",
        "title": "Quiénes Somos",
        "menu_label": "Quiénes Somos",
        "sort_order": 2,
        "content": {
            "hero_title": "Quiénes Somos",
            "p1": "En PIE 360 somos una plataforma integral diseñada para transformar la gestión del Programa de Integración Escolar. Nuestro propósito es brindar a los colegios una herramienta innovadora, segura y eficiente que les permita cumplir con la normativa vigente, optimizar tiempos administrativos y potenciar las intervenciones pedagógicas.",
            "p2": "Conocemos en detalle los desafíos normativos, administrativos y pedagógicos que enfrentan los establecimientos: Decreto 170, Ley de Inclusión, fiscalizaciones de la Superintendencia, elaboración de informes PAI/PACI, FUDEI, FUR y carpetas de respaldo.",
            "p3": "Nuestra misión es transformar la gestión del PIE en un proceso ágil, transparente y basado en datos, para que los colegios reduzcan tiempos administrativos, aseguren el cumplimiento normativo y potencien lo más importante: la intervención pedagógica y el desarrollo integral de cada estudiante.",
            "p4": "Con PIE 360 no solo entregamos una plataforma tecnológica, sino un ecosistema de innovación, trazabilidad y apoyo experto, diseñado para garantizar excelencia, seguridad y confiabilidad en cada etapa del proceso de integración escolar.",
            "image_url": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&h=600&fit=crop",
        },
    },
    {
        "slug": "what-we-do",
        "title": "Qué Hacemos",
        "menu_label": "Qué Hacemos",
        "sort_order": 3,
        "content": {
            "hero_title": "Qué Hacemos",
            "section_title": "Qué Hacemos",
            "section_subtitle": "Transformamos la gestión del PIE con tecnología innovadora",
            "benefits_title": "Beneficios para tu Colegio",
            "benefits_subtitle": "Optimiza recursos, ahorra tiempo y mejora resultados",
            "benefits_image": "/college_benefits.jpg",
            "features": [
                {
                    "icon": "mdi-cog-sync",
                    "color": "#ffc204",
                    "title": "Digitalización y Automatización",
                    "description": "Digitalizamos y automatizamos los procesos del PIE: evaluaciones, informes, planificaciones y carpetas de fiscalización.",
                },
                {
                    "icon": "mdi-monitor-dashboard",
                    "color": "#6eb715",
                    "title": "Panel Ejecutivo 360°",
                    "description": "Entregamos un panel ejecutivo 360° con datos en tiempo real, que facilita la toma de decisiones pedagógicas y administrativas.",
                },
                {
                    "icon": "mdi-account-group",
                    "color": "#00b8d4",
                    "title": "Comunicación con Apoderados",
                    "description": "Comunicación y participación activa de apoderados a través de nuestra plataforma integrada.",
                },
                {
                    "icon": "mdi-brain",
                    "color": "#ffc204",
                    "title": "Gestión Inteligente",
                    "description": "Profesionales trabajan con informes precargados y bancos de redacción para optimizar su tiempo.",
                },
                {
                    "icon": "mdi-shield-check",
                    "color": "#6eb715",
                    "title": "Seguridad y Trazabilidad",
                    "description": "Garantizamos seguridad, trazabilidad y cumplimiento con la normativa del Ministerio de Educación.",
                },
            ],
            "benefits": [
                "Menos burocracia, más intervención pedagógica",
                "Cumplimiento normativo y trazabilidad total",
                "Ahorro de tiempo administrativo (60% menos)",
                "Comunicación efectiva con familias",
                "Proyecciones y decisiones basadas en datos reales",
                "Escalable: funciona para 1 colegio o una red completa",
            ],
        },
    },
    {
        "slug": "services",
        "title": "Nuestros Servicios",
        "menu_label": "Servicios",
        "sort_order": 4,
        "content": {
            "hero_title": "Nuestros Servicios",
            "section_title": "Nuestros Servicios",
            "section_subtitle": "Soluciones completas para la gestión del PIE",
            "items": [
                {
                    "icon": "mdi-application",
                    "title": "Plataforma PIE 360°",
                    "description": "Sistema integral para la gestión completa del Programa de Integración Escolar.",
                },
                {
                    "icon": "mdi-clipboard-check",
                    "title": "Gestión de Evaluaciones",
                    "description": "Evaluaciones y re-evaluaciones con bancos de instrumentos y reportes automatizados.",
                },
                {
                    "icon": "mdi-folder-account",
                    "title": "Carpetas de Fiscalización",
                    "description": "Carpetas automáticas, listas para la Superintendencia de Educación.",
                },
                {
                    "icon": "mdi-chart-line",
                    "title": "Panel Multi-Colegio",
                    "description": "Panel ejecutivo con indicadores clave (KPIs) para múltiples establecimientos.",
                },
                {
                    "icon": "mdi-email-newsletter",
                    "title": "Comunicación con Familias",
                    "description": "Sistema de notificaciones y documentos compartidos con las familias.",
                },
                {
                    "icon": "mdi-account-tie",
                    "title": "Soporte y Capacitación",
                    "description": "Soporte bajo demanda, con manual digital y acompañamiento en línea.",
                },
            ],
        },
    },
    {
        "slug": "contact",
        "title": "Contacto",
        "menu_label": "Contacto",
        "sort_order": 5,
        "content": {
            "hero_title": "Contacto",
            "form_title": "¿Tienes alguna duda?",
            "form_subtitle": "Si estás interesado en la plataforma, necesitas ayuda o tienes alguna consulta, completa el formulario y nos pondremos en contacto contigo.",
        },
    },
    {
        "slug": "faq",
        "title": "Preguntas Frecuentes",
        "menu_label": "FAQ",
        "sort_order": 6,
        "content": {
            "hero_title": "Preguntas Frecuentes",
            "subtitle": "Encuentra respuestas a las dudas más comunes",
            "empty_title": "No hay preguntas frecuentes disponibles",
            "empty_text": "En este momento no hay FAQs para mostrar. Intenta más tarde.",
        },
    },
    {
        "slug": "downloads",
        "title": "Descargas",
        "menu_label": "Descargas",
        "sort_order": 7,
        "content": {
            "hero_title": "Descargas",
            "subtitle": "Accede a todos los recursos educativos y documentos",
            "empty_title": "No hay descargas disponibles",
            "empty_text": "En este momento no hay recursos para descargar. Intenta más tarde.",
        },
    },
    {
        "slug": "videos",
        "title": "Videos",
        "menu_label": "Videos",
        "sort_order": 8,
        "content": {
            "hero_title": "Videos",
            "subtitle": "Accede a nuestros recursos en video",
            "empty_title": "No hay videos disponibles",
            "empty_text": "En este momento no hay videos para mostrar. Intenta más tarde.",
        },
    },
    {
        "slug": "site",
        "title": "Sitio (global)",
        "menu_label": "Sitio / Footer",
        "sort_order": 99,
        "content": {
            "footer_copyright": "© 2025 Pie360 - Todos los derechos reservados | Desarrollado con ♥",
            "footer_terms_label": "Términos de uso",
            "footer_privacy_label": "Política de privacidad",
            "footer_company_title": "Empresa",
            "footer_resources_title": "Recursos",
            "footer_contact_title": "Contacto",
            "footer_social_title": "Síguenos",
            "platform_login_url": "https://pie-360-chile.web.app/login",
        },
    },
]


class WebPageClass:
    def __init__(self, db):
        self.db = db

    def _parse_content(self, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _to_dict(self, row: WebPageModel) -> dict[str, Any]:
        return {
            "id": row.id,
            "slug": row.slug,
            "title": row.title,
            "menu_label": row.menu_label,
            "sort_order": row.sort_order,
            "is_published": int(row.is_published or 0),
            "content": self._parse_content(row.content_json),
            "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S") if row.added_date else None,
            "updated_date": row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if row.updated_date else None,
        }

    def ensure_defaults(self) -> None:
        """Crea páginas faltantes y completa claves de content faltantes."""
        rows = self.db.query(WebPageModel).all()
        by_slug = {r.slug: r for r in rows}
        now = datetime.now()
        changed = False
        for page in DEFAULT_PAGES:
            slug = page["slug"]
            defaults = page.get("content") or {}
            if slug not in by_slug:
                self.db.add(
                    WebPageModel(
                        slug=slug,
                        title=page["title"],
                        menu_label=page.get("menu_label") or page["title"],
                        sort_order=int(page.get("sort_order") or 0),
                        is_published=1,
                        content_json=json.dumps(defaults, ensure_ascii=False),
                        added_date=now,
                        updated_date=now,
                    )
                )
                changed = True
                continue
            row = by_slug[slug]
            current = self._parse_content(row.content_json)
            merged = False
            for key, value in defaults.items():
                if key not in current:
                    current[key] = value
                    merged = True
            if merged:
                row.content_json = json.dumps(current, ensure_ascii=False)
                row.updated_date = now
                changed = True
        if changed:
            self.db.commit()

    def get_all(self, *, published_only: bool = False) -> list[dict[str, Any]]:
        self.ensure_defaults()
        q = self.db.query(WebPageModel)
        if published_only:
            q = q.filter(WebPageModel.is_published == 1)
        rows = q.order_by(WebPageModel.sort_order.asc(), WebPageModel.id.asc()).all()
        return [self._to_dict(r) for r in rows]

    def get_by_id(self, page_id: int) -> dict[str, Any] | None:
        self.ensure_defaults()
        row = self.db.query(WebPageModel).filter(WebPageModel.id == page_id).first()
        return self._to_dict(row) if row else None

    def get_by_slug(self, slug: str, *, published_only: bool = True) -> dict[str, Any] | None:
        self.ensure_defaults()
        q = self.db.query(WebPageModel).filter(WebPageModel.slug == slug)
        if published_only:
            q = q.filter(WebPageModel.is_published == 1)
        row = q.first()
        return self._to_dict(row) if row else None

    def update(self, page_id: int, data: dict[str, Any]) -> dict[str, Any]:
        row = self.db.query(WebPageModel).filter(WebPageModel.id == page_id).first()
        if not row:
            return {"status": "error", "message": "Página no encontrada"}
        try:
            if "title" in data and data["title"] is not None:
                row.title = str(data["title"]).strip() or row.title
            if "menu_label" in data:
                row.menu_label = (str(data["menu_label"]).strip() if data["menu_label"] else None)
            if "sort_order" in data and data["sort_order"] is not None:
                row.sort_order = int(data["sort_order"])
            if "is_published" in data and data["is_published"] is not None:
                row.is_published = 1 if int(data["is_published"]) else 0
            if "content" in data and data["content"] is not None:
                content = data["content"]
                if isinstance(content, str):
                    content = json.loads(content)
                if not isinstance(content, dict):
                    return {"status": "error", "message": "content debe ser un objeto JSON"}
                row.content_json = json.dumps(content, ensure_ascii=False)
            row.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(row)
            return {"status": "success", "message": "Página actualizada", "data": self._to_dict(row)}
        except Exception as exc:
            self.db.rollback()
            return {"status": "error", "message": str(exc)}
