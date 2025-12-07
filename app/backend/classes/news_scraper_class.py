import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app.backend.db.models import NewsModel
from sqlalchemy.orm import Session
import locale
import re

class NewsScraperClass:
    def __init__(self, db: Session):
        self.db = db
        self.url = "https://especial.mineduc.cl/destacados/"
    
    def parse_spanish_date(self, date_str):
        """
        Convierte fecha en español a datetime
        Ejemplo: "Martes 25 de Noviembre, 2025" -> datetime
        """
        try:
            # Mapeo de meses en español
            meses = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            
            # Extraer día, mes y año
            # Formato: "Martes 25 de Noviembre, 2025" o "Jueves 06 de Noviembre, 2025"
            parts = date_str.lower().split()
            dia = int(parts[1])
            mes_str = parts[3].replace(',', '')  # Remover la coma del mes
            anio = int(parts[4].replace(',', ''))
            
            mes = meses.get(mes_str, 1)
            
            result = datetime(anio, mes, dia)
            print(f"DEBUG - Fecha parseada: '{date_str}' -> día={dia}, mes={mes} ({mes_str}), año={anio} -> resultado={result}")
            
            return result
        except Exception as e:
            print(f"Error parseando fecha '{date_str}': {str(e)}")
            return datetime.now()
    
    def get_news_detail(self, url, headers):
        """
        Obtiene el detalle completo de una noticia individual
        """
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar el título en la página de detalle
            title = ""
            
            # Primero buscar específicamente el título de la entrada
            title_tag = soup.find('h1', class_='entry-title')
            
            # Si no existe, buscar otros h1 pero excluir el del sitio
            if not title_tag:
                all_h1 = soup.find_all('h1')
                for h1 in all_h1:
                    h1_text = h1.get_text(strip=True)
                    # Excluir títulos genéricos del sitio
                    if h1_text and h1_text not in ['Ministerio de Educación', 'Educación Especial'] and len(h1_text) > 10:
                        title_tag = h1
                        break
            
            # Si aún no hay, buscar en h2
            if not title_tag:
                title_tag = soup.find('h2', class_='post-title') or soup.find('h2', class_='entry-title')
            
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            print(f"Título extraído: '{title}'")
            
            # Si no hay título válido, omitir esta noticia
            if not title or len(title) < 10 or title in ['Ministerio de Educación', 'Educación Especial']:
                print(f"Título inválido o genérico, omitiendo noticia")
                return None
            
            # Buscar el contenido principal
            content = soup.find('div', class_='entry-content') or soup.find('article') or soup.find('div', class_='content')
            
            # Descripción completa: todos los párrafos
            description = ""
            if content:
                paragraphs = content.find_all('p')
                description = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Si no hay descripción, omitir esta noticia
            if not description or len(description) < 50:
                return None
            
            # Descripción corta: primeros 150 caracteres de la descripción completa
            short_description = description[:147] + "..." if len(description) > 150 else description
            
            # Buscar la imagen en múltiples ubicaciones
            image_url = ""
            
            # 1. Buscar imagen destacada en el header/article
            img_tag = soup.find('img', class_='attachment-post-thumbnail') or soup.find('img', class_='wp-post-image')
            
            # 2. Buscar en el contenido (puede estar arriba o abajo)
            if not img_tag and content:
                img_tag = content.find('img')
            
            # 3. Buscar en cualquier parte del article
            if not img_tag:
                article = soup.find('article')
                if article:
                    img_tag = article.find('img')
            
            # 4. Buscar cualquier imagen en la página principal
            if not img_tag:
                img_tag = soup.find('img')
            
            if img_tag:
                image_url = img_tag.get('src', '') or img_tag.get('data-src', '') or img_tag.get('data-lazy-src', '')
                # Convertir URL relativa a absoluta
                if image_url and not image_url.startswith('http'):
                    if image_url.startswith('/'):
                        image_url = f"https://especial.mineduc.cl{image_url}"
                    else:
                        image_url = f"https://especial.mineduc.cl/{image_url}"
            
            # Si no hay imagen, omitir esta noticia
            if not image_url:
                return None
            
            return {
                'title': title,
                'short_description': short_description,
                'description': description,
                'image': image_url
            }
        except Exception as e:
            print(f"Error obteniendo detalle de {url}: {str(e)}")
            return None
    
    def scrape_news(self):
        """
        Scraper para obtener noticias del MINEDUC y guardarlas en la base de datos
        """
        try:
            # Realizar petición a la página
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parsear HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar todos los contenedores de noticias (div.box dentro de div.row)
            news_boxes = soup.find_all('div', class_='box')
            
            saved_count = 0
            skipped_count = 0
            
            print(f"Total de noticias encontradas: {len(news_boxes)}")
            
            for box in news_boxes:
                try:
                    # Buscar el enlace principal de la noticia (el segundo <a> que no es .thumb)
                    links = box.find_all('a', href=True)
                    url = None
                    
                    for link in links:
                        href = link.get('href', '')
                        # Buscar el enlace que no es .thumb y no es .vermas
                        if href and 'especial.mineduc.cl' in href and 'thumb' not in link.get('class', []) and 'vermas' not in link.get('class', []):
                            url = href
                            break
                    
                    if not url:
                        continue
                    
                    # Extraer la fecha desde el box (span.fecha)
                    fecha_tag = box.find('span', class_='fecha')
                    fecha_str = fecha_tag.get_text(strip=True) if fecha_tag else None
                    news_date = self.parse_spanish_date(fecha_str) if fecha_str else None
                    
                    print(f"Procesando noticia: {url}")
                    
                    # Obtener el detalle completo de la noticia
                    news_detail = self.get_news_detail(url, headers)
                    
                    if not news_detail or not news_detail['title']:
                        print(f"No se pudo obtener detalle de: {url}")
                        continue
                    
                    title = news_detail['title']
                    short_description = news_detail['short_description']
                    description = news_detail['description']
                    image_url = news_detail['image']
                    
                    print(f"Título encontrado: {title[:50]}...")
                    
                    # Verificar si la noticia ya existe en la base de datos
                    existing_news = self.db.query(NewsModel).filter(
                        NewsModel.title == title,
                        NewsModel.deleted_status_id == 0
                    ).first()
                    
                    if existing_news:
                        print(f"Noticia ya existe: {title[:50]}...")
                        skipped_count += 1
                        continue
                    
                    # Crear nueva noticia
                    print(f"Creando noticia con título: '{title}' - Fecha: {news_date}")
                    new_news = NewsModel(
                        deleted_status_id=0,
                        title=title,
                        short_description=short_description,
                        description=description,
                        image=image_url,
                        added_date=news_date if news_date else datetime.now(),
                        updated_date=datetime.now()
                    )
                    
                    self.db.add(new_news)
                    self.db.flush()  # Forzar escritura inmediata
                    saved_count += 1
                    print(f"Noticia agregada a la sesión: {title[:50]}...")
                    
                except Exception as e:
                    print(f"Error procesando noticia individual: {str(e)}")
                    continue
            
            # Guardar cambios
            print(f"Intentando guardar {saved_count} noticias en la base de datos...")
            try:
                self.db.commit()
                print(f"Commit exitoso!")
                
                # Verificar que se guardaron
                count = self.db.query(NewsModel).filter(NewsModel.deleted_status_id == 0).count()
                print(f"Total de noticias en la BD después del commit: {count}")
                
            except Exception as e:
                print(f"Error en commit: {str(e)}")
                self.db.rollback()
                raise
            
            return {
                "status": "success",
                "message": f"Scraping completado. {saved_count} noticias guardadas, {skipped_count} omitidas (duplicadas)",
                "saved": saved_count,
                "skipped": skipped_count
            }
            
        except requests.RequestException as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Error al realizar petición HTTP: {str(e)}"
            }
        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": f"Error en el scraping: {str(e)}"
            }
