import requests
import gzip
import xml.etree.ElementTree as ET
import io
import json
import os
import hashlib
import random
import re
from datetime import datetime

# URL do feed
feed_url = "https://feeds.whatjobs.com/sinerj/sinerj_pt_BR.xml.gz"

# Pasta JSON
json_folder = "json_parts"
os.makedirs(json_folder, exist_ok=True)

file_count = 1

# Cidade alvo
cidades_desejadas = ["campinas"]

def normalizar(texto):
    return texto.strip().lower()

def gerar_id_unico(titulo, empresa, cidade, url):
    base = f"{titulo}-{empresa}-{cidade}-{url}"
    return hashlib.md5(base.encode()).hexdigest()

def gerar_slug(titulo, cidade):
    texto = f"{titulo}-{cidade}"
    texto = texto.lower()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"\s+", "-", texto)
    return texto

def limpar_html(texto):
    texto = re.sub(r"<[^>]+>", "", texto)
    return texto.strip()

# 🔥 VARIAÇÕES DE INTRO (ANTI-DUPLICAÇÃO)
def gerar_intro(titulo, cidade):
    intros = [
        f"Confira a oportunidade para {titulo} em {cidade}. Veja requisitos e como se candidatar.",
        f"Nova vaga disponível para {titulo} em {cidade}. Saiba mais sobre essa oportunidade.",
        f"Empresa está contratando {titulo} em {cidade}. Veja detalhes e envie seu currículo."
    ]
    return random.choice(intros)

# Baixar feed
try:
    response = requests.get(feed_url, stream=True, timeout=60)
except requests.exceptions.RequestException as e:
    print(f"Erro ao baixar o feed: {e}")
    exit(1)

if response.status_code == 200:
    with gzip.open(io.BytesIO(response.content), "rt", encoding="utf-8") as f:

        jobs = []
        urls_vistas = set()  # evitar duplicados

        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag == "job":

                location_elem = elem.find("locations/location")
                city = location_elem.findtext("city", "").strip() if location_elem is not None else ""
                state = location_elem.findtext("state", "").strip() if location_elem is not None else ""

                if not city or not state:
                    elem.clear()
                    continue

                city_lower = normalizar(city)

                if city_lower in cidades_desejadas:

                    title = elem.findtext("title", "").strip()
                    description = elem.findtext("description", "").strip()

                    company = elem.findtext("company/name", "").strip()
                    if not company:
                        company = "Confidencial"

                    url = elem.findtext("urlDeeplink", "").strip()
                    tipo = elem.findtext("jobType", "").strip()

                    # ❌ Evitar duplicados
                    if url in urls_vistas:
                        elem.clear()
                        continue
                    urls_vistas.add(url)

                    # 🔥 LIMPAR HTML
                    description = limpar_html(description)

                    # 🔥 INTRO DINÂMICA
                    intro = gerar_intro(title, city)

                    descricao_final = intro + "\n\n" + description

                    # 🔥 ID ÚNICO
                    job_id = gerar_id_unico(title, company, city, url)

                    # 🔥 SLUG SEO
                    slug = gerar_slug(title, city)

                    # 🔥 DATA
                    data_publicacao = datetime.utcnow().isoformat()

                    job_data = {
                        "id": job_id,
                        "title": title,
                        "slug": slug,
                        "description": descricao_final,
                        "company": company,
                        "city": city,
                        "state": state,
                        "url": url,
                        "tipo": tipo,
                        "data_publicacao": data_publicacao
                    }

                    jobs.append(job_data)

                elem.clear()

                # Salvar a cada 1000
                if len(jobs) >= 1000:
                    json_path = os.path.join(json_folder, f"part_{file_count}.json")

                    with open(json_path, "w", encoding="utf-8") as json_file:
                        json.dump(jobs, json_file, ensure_ascii=False, indent=2)

                    print(f"Arquivo salvo: {json_path}")

                    jobs = []
                    file_count += 1

        # Final
        if jobs:
            json_path = os.path.join(json_folder, f"part_{file_count}.json")

            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(jobs, json_file, ensure_ascii=False, indent=2)

            print(f"Arquivo final salvo: {json_path}")

    print(f"JSONs gerados: {os.listdir(json_folder)}")

else:
    print(f"Erro ao baixar o feed: código HTTP {response.status_code}")
    exit(1)
