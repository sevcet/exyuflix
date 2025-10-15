from yt_dlp import YoutubeDL
import xml.etree.ElementTree as ET
import os
import requests
import re
import time
import json

# TMDB API KLJUČ
TMDB_API_KEY = "e35d7c6d923368eb473f6ed8c97658c5"

class RobustTranslator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.translated_count = 0
        self.error_count = 0
        
    def translate_text(self, text, max_retries=3):
        """
        Robustan prevod sa automatskim oporavkom od grešaka
        """
        if not text or text.strip() == "":
            return text
            
        # Proveri da li tekst sadrži "..." - preskoči prevod ako ima
        if "..." in text:
            print("  ⏭️  Tekst sadrži '...' - preskačem prevod")
            return text
            
        # Proveri da li je tekst već na srpskom
        if self.is_serbian_text(text):
            return text
            
        for attempt in range(max_retries):
            try:
                # Podeli duže tekstove na delove ako je potrebno
                if len(text) > 1500:
                    return self.translate_long_text(text)
                
                # Prvo pokušaj sa MyMemory API
                translated = self.try_mymemory_translate(text)
                if translated and translated != text:
                    return self.to_latin(translated)
                
                # Fallback na Google Translate
                translated = self.try_google_translate(text)
                if translated and translated != text:
                    return self.to_latin(translated)
                    
                raise Exception("Svi API-ji su vratili prazan odgovor")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"✗ Greška pri prevodu (pokušaj {attempt + 1}): {error_msg}")
                
                # Proveri specifične greške i prilagodi pauzu
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    wait_time = 10  # Duža pauza za mrežne greške
                elif "429" in error_msg or "rate" in error_msg.lower():
                    wait_time = 30  # Duža pauza za rate limiting
                else:
                    wait_time = 5
                
                if attempt < max_retries - 1:
                    print(f"🕐 Čekam {wait_time} sekundi pre ponovnog pokušaja...")
                    time.sleep(wait_time)
                else:
                    self.error_count += 1
                    print(f"❌ Konačna greška za tekst: {text[:50]}...")
                    return text
    
    def to_latin(self, text):
        """Konvertuje ćirilični tekst u latinicu"""
        if not text:
            return text
            
        # Rečnik za konverziju ćirilice u latinicu
        cirilica_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ђ': 'đ', 'е': 'e', 'ж': 'ž',
            'з': 'z', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm', 'н': 'n',
            'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ћ': 'ć', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'č', 'џ': 'dž', 'ш': 'š',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Ђ': 'Đ', 'Е': 'E', 'Ж': 'Ž',
            'З': 'Z', 'И': 'I', 'Ј': 'J', 'К': 'K', 'Л': 'L', 'Љ': 'Lj', 'М': 'M', 'Н': 'N',
            'Њ': 'Nj', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'Ћ': 'Ć', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Č', 'Џ': 'Dž', 'Ш': 'Š'
        }
        
        # Konvertuj ćirilične karaktere
        result = []
        i = 0
        while i < len(text):
            char = text[i]
            
            # Proveri za dvoslovne kombinacije prvo
            if i < len(text) - 1:
                two_chars = text[i:i+2]
                if two_chars in ['љ', 'њ', 'џ', 'Љ', 'Њ', 'Џ']:
                    result.append(cirilica_to_latin.get(two_chars, two_chars))
                    i += 2
                    continue
            
            # Konvertuj pojedinačne karaktere
            result.append(cirilica_to_latin.get(char, char))
            i += 1
        
        return ''.join(result)
    
    def try_mymemory_translate(self, text):
        """Pokušaj prevoda preko MyMemory API"""
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text,
                'langpair': 'en|sr',
                'de': 'user@example.com'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data['responseStatus'] == 200:
                translated_text = data['responseData']['translatedText']
                return self.clean_translated_text(translated_text)
            
        except Exception as e:
            print(f"  MyMemory greška: {e}")
            return None
    
    def try_google_translate(self, text):
        """Pokušaj prevoda preko Google Translate API"""
        try:
            # Koristimo jednostavniji pristup za Google Translate
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                'client': 'gtx',
                'sl': 'en',
                'tl': 'sr',
                'dt': 't',
                'q': text
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            translated_text = ""
            
            # Google vraća kompleksan JSON, ekstraktujemo prevod
            if data and len(data) > 0 and data[0]:
                for segment in data[0]:
                    if segment[0]:
                        translated_text += segment[0]
            
            return self.clean_translated_text(translated_text) if translated_text else None
            
        except Exception as e:
            print(f"  Google Translate greška: {e}")
            return None
    
    def translate_long_text(self, text):
        """Podeli duži tekst na delove i prevedi pojedinačno"""
        print(f"  📖 Tekst je dug ({len(text)} karaktera), delim na delove...")
        
        # Podeli tekst na rečenice
        sentences = re.split(r'(?<=[.!?])\s+', text)
        translated_parts = []
        
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) > 20:  # Prevedi samo značajne rečenice
                # Proveri da li rečenica sadrži "..." - preskoči prevod ako ima
                if "..." in sentence:
                    print(f"    ⏭️  Deo {i+1} sadrži '...' - preskačem prevod")
                    translated_parts.append(sentence.strip())
                else:
                    print(f"    Prevodim deo {i+1}/{len(sentences)}...")
                    translated_sentence = self.translate_text(sentence.strip())
                    translated_parts.append(translated_sentence)
                    time.sleep(1)  # Pauza između delova
            else:
                translated_parts.append(sentence)
        
        return ' '.join(translated_parts)
    
    def is_serbian_text(self, text):
        """Proverava da li tekst već sadrži srpska slova (i ćirilična i latinična)"""
        srpski_pattern = re.compile(r'[šđčćžŠĐČĆŽ]', re.IGNORECASE)
        return bool(srpski_pattern.search(text))
    
    def clean_translated_text(self, text):
        """Čišćenje prevedenog teksta"""
        if not text:
            return text
            
        # Osnovno čišćenje
        text = text.replace('&#39;', "'").replace('&quot;', '"')
        text = re.sub(r'\s+', ' ', text)  # Normalizuj razmake
        
        # Popravi česte greške u prevodu
        corrections = {
            'Čeka se soba': 'Čekaonica',
            'soba za čekanje': 'čekaonica',
            '1. priča': 'PRVA PRIČA',
            '2. priča': 'DRUGA PRIČA', 
            '3. priča': 'TREĆA PRIČA',
            '1st': 'PRVA',
            '2nd': 'DRUGA',
            '3rd': 'TREĆA',
            'STORY': 'PRIČA',
        }
        
        for wrong, correct in corrections.items():
            text = text.replace(wrong, correct)
        
        return text.strip()

def clean_movie_title(title):
    """Čisti YouTube naslove - POBOLJŠANA VERZIJA"""
    # Konvertuj prvo u latinicu ako je ćirilica
    translator = RobustTranslator()
    title = translator.to_latin(title)
    
    # Uklanja sve u zagradama i uglastim zagradama
    clean_title = re.sub(r'[\(\[].*?[\)\]]', '', title)
    
    # Uklanja "Ceo film", "Full Movie" itd. - POBOLJŠANO
    patterns_to_remove = [
        r'(?i)ceo film', r'(?i)full movie', r'(?i)film', r'(?i)movie',
        r'(?i)english subbed?', r'(?i)hd', r'(?i)domaći film', r'(?i)domaci film',
        r'(?i)domaći', r'(?i)online', r'(?i)download', r'(?i)free',
        r'(?i)youtube', r'(?i)preuzmi', r'(?i)gledaj', r'(?i)rezija',
        r'(?i)subtitle', r'(?i)subtitled', r'(?i)trailer', r'(?i)official',
        r'\d{3,4}p', r'\d+k', r'\[.*?\]', r'\(.*?\)'
    ]
    
    for pattern in patterns_to_remove:
        clean_title = re.sub(pattern, '', clean_title)
    
    # Uklanja režisera ako je nakon " - " ili " | "
    clean_title = re.split(r'[-|]', clean_title)[0]
    
    # Uklanja višestruke razmake i specijalne karaktere
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    # Uklanja vodiće razmake i tačke
    clean_title = re.sub(r'^[\.\s]+|[\.\s]+$', '', clean_title)
    
    print(f"🧹 Očišćen naslov: '{clean_title}'")
    return clean_title

def get_existing_video_ids():
    """Čita postojeći XML i vraća set postojećih videoId-eva"""
    existing_ids = set()
    
    if os.path.exists("domaci_filmovi.xml"):
        try:
            tree = ET.parse("domaci_filmovi.xml")
            root = tree.getroot()
            
            for movie in root.findall('movie'):
                video_id_elem = movie.find('videoId')
                if video_id_elem is not None and video_id_elem.text:
                    existing_ids.add(video_id_elem.text)
            
            print(f"📁 Pronađeno {len(existing_ids)} postojećih videoId-eva u domaci_filmovi.xml")
        except Exception as e:
            print(f"⚠️ Greška pri čitanju postojećeg XML-a: {e}")
    
    return existing_ids

def get_movie_info(title):
    """Traži informacije o filmu na TMDB - POBOLJŠANA VERZIJA"""
    try:
        clean_title = clean_movie_title(title)
        print(f"🔍 TMDB pretraga: '{clean_title}'")
        
        # TMDB API pretraga - TRAŽIMO NA ENGLESKOM
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={clean_title}&language=en-US"
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['results']:
                movie = data['results'][0]
                year = movie['release_date'][:4] if movie.get('release_date') else 'N/A'
                description = movie['overview'] if movie.get('overview') else 'Opis nije dostupan'
                
                print(f"✅ Pronađen: {movie['title']} ({year})")
                return {
                    'year': year,
                    'description': description,
                    'found': True
                }
            else:
                print(f"❌ Nema rezultata u TMDB")
        else:
            print(f"❌ TMDB greška: {response.status_code}")
        
        return {
            'year': 'N/A',
            'description': '...',
            'found': False
        }
        
    except Exception as e:
        print(f"⚠️ Greška: {e}")
        return {
            'year': 'N/A', 
            'description': 'Greška pri pretrazi',
            'found': False
        }

def get_playlist_videos(playlist_url):
    """Dobija sve video zapise iz playliste"""
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(playlist_url, download=False)
            return result['entries']
    except Exception as e:
        print(f"❌ Greška: {e}")
        return []

def save_formatted_xml(tree, output_file):
    """Čuva XML u lepo formatiranom obliku"""
    root = tree.getroot()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<movies>\n')
        
        for movie in root.findall('movie'):
            f.write('    <movie>\n')
            
            for elem in movie:
                tag = elem.tag
                text = elem.text if elem.text else ""
                
                if tag == 'title':
                    # Očisti title - POBOLJŠANA VERZIJA
                    cleaned_title = clean_movie_title(text)
                    f.write(f'        <title>{cleaned_title}</title>\n')
                else:
                    f.write(f'        <{tag}>{text}</{tag}>\n')
            
            f.write('    </movie>\n')
        
        f.write('</movies>\n')

def process_existing_titles():
    """Procesira postojeće naslove u XML-u - konvertuje u latinicu i čisti"""
    if not os.path.exists("domaci_filmovi.xml"):
        print("❌ Postojeći XML fajl ne postoji")
        return
    
    try:
        # Učitaj postojeći XML
        tree = ET.parse("domaci_filmovi.xml")
        root = tree.getroot()
        
        processed_count = 0
        
        print("🔄 Procesiram postojeće naslove...")
        
        for movie in root.findall('movie'):
            title_elem = movie.find('title')
            if title_elem is not None and title_elem.text:
                original_title = title_elem.text
                cleaned_title = clean_movie_title(original_title)
                
                if cleaned_title != original_title:
                    title_elem.text = cleaned_title
                    processed_count += 1
                    print(f"  ✅ Očišćen naslov: '{original_title}' -> '{cleaned_title}'")
        
        if processed_count > 0:
            # Sačuvaj ažurirani XML
            save_formatted_xml(tree, "domaci_filmovi_cleaned.xml")
            print(f"\n🎉 Ažurirano {processed_count} naslova u domaci_filmovi_cleaned.xml")
        else:
            print("ℹ️  Nema naslova za obradu")
            
    except Exception as e:
        print(f"❌ Greška pri procesiranju postojećih naslova: {e}")

def create_xml_with_translation():
    """Kreira NOVI XML fajl samo sa novim videoId-evi i prevodi opise"""
    playlist_url = "https://www.youtube.com/playlist?list=PLFTGssSZfmnSTvinoEMacILHl7KCrrZia"
    
    print("🔍 Učitavam playlistu sa YouTube-a...")
    
    videos = get_playlist_videos(playlist_url)
    
    if not videos:
        print("❌ Nisam uspeo da dobijem podatke sa YouTube-a")
        return
    
    print(f"✅ Pronađeno {len(videos)} video zapisa!")
    
    # Učitaj postojeće videoId-eve
    existing_video_ids = get_existing_video_ids()
    
    # Kreiraj NOVI XML root
    new_root = ET.Element("movies")
    
    # Inicijalizuj translator
    translator = RobustTranslator()
    
    # Prvo kopiraj SVE postojeće filmove iz starog XML-a
    if os.path.exists("domaci_filmovi.xml"):
        try:
            existing_tree = ET.parse("domaci_filmovi.xml")
            existing_root = existing_tree.getroot()
            
            # Kopiraj sve postojeće filmove
            for movie in existing_root.findall('movie'):
                new_root.append(movie)
            
            print(f"📋 Kopirano {len(existing_root.findall('movie'))} postojećih filmova")
            
        except Exception as e:
            print(f"⚠️ Greška pri kopiranju postojećeg XML-a: {e}")
    
    # Sada dodaj SAMO NOVE filmove iz playliste i prevodi opise
    print("\n🌐 Tražim nove filmove, povezujem se sa TMDB i prevodim opise...")
    
    new_movies_count = 0
    found_in_tmdb_count = 0
    translated_count = 0
    
    for i, video in enumerate(videos, 1):
        video_id = video['id']
        video_title = video['title']
        
        # Preskoči ako već postoji u XML-u
        if video_id in existing_video_ids:
            print(f"⏭️  {i}. Preskočen: '{video_title}' (već postoji)")
            continue
        
        print(f"\n🎬 {i}. NOVI FILM: '{video_title}'")
        print(f"   🆔 Video ID: {video_id}")
        
        # Očisti naslov
        cleaned_title = clean_movie_title(video_title)
        
        # Traži informacije o filmu
        movie_info = get_movie_info(video_title)
        
        if movie_info['found']:
            found_in_tmdb_count += 1
            
            # PREVOD OPISA NA SRPSKI
            original_description = movie_info['description']
            print(f"   📝 Originalni opis ({len(original_description)} karaktera): {original_description[:80]}...")
            
            # Prevedi opis samo ako nije "Opis nije dostupan" ili "..." i ako nije na srpskom
            if (original_description and 
                original_description != "Opis nije dostupan" and 
                "..." not in original_description and
                not translator.is_serbian_text(original_description)):
                
                print("   🌍 Prevodim opis na srpski...")
                translated_description = translator.translate_text(original_description)
                
                if translated_description and translated_description != original_description:
                    movie_info['description'] = translated_description
                    translated_count += 1
                    translator.translated_count += 1
                    print(f"   ✅ OPIS PREVEDEN NA SRPSKI!")
                    print(f"   📄 Prevedeno: {translated_description[:80]}...")
                    
                    # Pauza između prevoda da izbegnemo rate limiting
                    time.sleep(3)
                else:
                    print("   ⚠️  Opis nije preveden")
            else:
                print("   ⏭️  Opis ne zahteva prevod")
        
        # Kreiraj NOVI movie element
        movie_elem = ET.SubElement(new_root, "movie")
        
        title_elem = ET.SubElement(movie_elem, "title")
        title_elem.text = cleaned_title  # Koristi očišćen naslov
        
        year_elem = ET.SubElement(movie_elem, "year")
        year_elem.text = movie_info['year']
        
        genre_elem = ET.SubElement(movie_elem, "genre")
        genre_elem.text = "Domaci film"
        
        type_elem = ET.SubElement(movie_elem, "type")
        type_elem.text = "film"
        
        description_elem = ET.SubElement(movie_elem, "description")
        description_elem.text = movie_info['description']
        
        image_elem = ET.SubElement(movie_elem, "imageUrl")
        image_elem.text = f"https://img.youtube.com/vi/{video_id}/0.jpg"
        
        video_id_elem = ET.SubElement(movie_elem, "videoId")
        video_id_elem.text = video_id
        
        new_movies_count += 1
        print(f"   ✅ DODAT U XML: '{cleaned_title}'")
    
    # Snimi NOVI XML SA LEPŠIM FORMATIRANJEM
    tree = ET.ElementTree(new_root)
    output_file = "domaci_filmovi_1.xml"
    
    save_formatted_xml(tree, output_file)
    
    file_path = os.path.abspath(output_file)
    
    # Prebroj ukupno filmova u novom XML-u
    total_movies = len(new_root.findall('movie'))
    
    print(f"\n🎉 NOVI XML fajl je kreiran: {file_path}")
    print(f"📊 STATISTIKA:")
    print(f"   • Ukupno filmova u novom XML-u: {total_movies}")
    print(f"   • Postojećih filmova: {total_movies - new_movies_count}")
    print(f"   • Novih filmova dodato: {new_movies_count}")
    print(f"   • Novih filmova pronađeno u TMDB: {found_in_tmdb_count}")
    print(f"   • Opisa prevedeno na srpski: {translated_count}")
    
    if new_movies_count == 0:
        print(f"\n💡 Nema novih filmova za dodavanje! Playlista je ažurirana.")

if __name__ == "__main__":
    print("🎬 DOMAĆI FILMOVI - XML GENERATOR SA PREVODOM")
    print("=" * 50)
    print("1. Kreiraj novi XML sa novim filmovima (preporučeno)")
    print("2. Očisti postojeće naslove u XML-u")
    
    choice = input("\nOdaberite opciju (1 ili 2): ").strip()
    
    if choice == "2":
        process_existing_titles()
    else:
        create_xml_with_translation()
    
    print("\n🎉 Proces završen!")