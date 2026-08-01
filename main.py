import os
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from sanitize_filename import sanitize

IMAGE_URL = (
    "https://content.img-gorod.ru/pim/products/images/be/30/01907874-17a3-7818-9447-9f5b9d3dbe30.jpg"
)
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FOLDER = BASE_DIR / "images11"
BOOKS_FOLDER = BASE_DIR / "books"
LIBRARY_URL = "https://knigofil.org/"
TOP_URL = "https://knigofil.org/top-100.html"


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def get_filename_from_url(url: str) -> str:
    url_path = urlsplit(url).path
    filename = os.path.split(url_path)[1]
    filename = unquote(filename)
    if not filename:
        filename = "downloaded_image.jpg"
    name, extension = os.path.splitext(filename)
    if not extension:
        filename = f"{name}.jpg"
    return filename


def fetch_page(url: str) -> str:
    """Получить HTML содержимое страницы."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


# ---------------------------------------------------------------------------
# Парсинг: ссылки на книги
# ---------------------------------------------------------------------------

def get_all_book_links(html: str) -> list[str]:
    """Получить уникальные ссылки на книги со страницы (новинки, class=book-link)."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []

    for a in soup.find_all("a", class_="book-link"):
        href: str = str(a.get("href") or "")
        if not href:
            continue
        if href.startswith("/"):
            href = LIBRARY_URL.rstrip("/") + href
        elif not href.startswith("http"):
            href = LIBRARY_URL.rstrip("/") + "/" + href
        if href not in seen:
            seen.add(href)
            links.append(href)

    return links


def get_top_book_links(html: str) -> list[str]:
    """Шаг 15: получить ссылки на книги со страницы топ-100 (li.tops-item)."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []

    for item in soup.find_all("li", class_="tops-item"):
        a = item.find("a", href=True)
        if not a:
            continue
        href: str = str(a.get("href") or "")
        if not href:
            continue
        if href.startswith("/"):
            href = LIBRARY_URL.rstrip("/") + href
        elif not href.startswith("http"):
            href = LIBRARY_URL.rstrip("/") + "/" + href
        if href not in seen:
            seen.add(href)
            links.append(href)

    return links


# ---------------------------------------------------------------------------
# Парсинг: данные книги
# ---------------------------------------------------------------------------

def get_book_info(book_page_html: str) -> dict:
    """Получить название, автора, жанр и год издания книги."""
    soup = BeautifulSoup(book_page_html, "html.parser")

    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    author = ""
    genre = ""
    year = ""

    for stat in soup.find_all("div", class_="big-book-stat"):
        span = stat.find("span")
        if not span:
            continue
        key = span.get_text(strip=True).rstrip(":")
        values = [a.get_text(strip=True) for a in stat.find_all("a")]
        value = " / ".join(values)
        if key == "Автор":
            author = value
        elif key == "Жанр":
            genre = value
        elif key == "Год":
            year = value

    return {"title": title, "author": author, "genre": genre, "year": year}


def get_book_image_url(book_page_html: str, base_url: str) -> str | None:
    """Получить ссылку на обложку книги."""
    soup = BeautifulSoup(book_page_html, "html.parser")

    img = None
    container = soup.find("div", class_="big-book-left-block")
    if container:
        img = container.find("img")

    if not img:
        container = soup.find("div", class_="book-wrapper")
        if container:
            img = container.find("img")

    if not img:
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src") or ""
            if "uploads/posts" in src:
                img = img_tag
                break

    if img:
        image_url = str(img.get("src") or "")
        if image_url:
            return urljoin(base_url, image_url)

    return None


def get_book_txt_url(book_page_html: str, base_url: str) -> str | None:
    """Получить ссылку на txt-файл книги."""
    soup = BeautifulSoup(book_page_html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "")
        if href.endswith(".txt"):
            return urljoin(base_url, href)
    return None


# ---------------------------------------------------------------------------
# Загрузка файлов
# ---------------------------------------------------------------------------

def download_image(url: str, output_folder: str | Path = OUTPUT_FOLDER) -> str:
    """Скачать изображение и сохранить в папку."""
    filename = get_filename_from_url(url)
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)
    output_path = output_folder_path / filename

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return str(output_path)


def download_book_text(
    txt_url: str, title: str, output_folder: str | Path = BOOKS_FOLDER
) -> str:
    """Скачать текст книги (.txt) и сохранить в папку."""
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    filename = sanitize(title or get_filename_from_url(txt_url))
    if not filename.endswith(".txt"):
        filename += ".txt"
    output_path = output_folder_path / filename

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(txt_url, headers=headers, timeout=30)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return str(output_path)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    # Шаг 2-3: скачать одну обложку по прямому URL
    saved_file = download_image(IMAGE_URL, OUTPUT_FOLDER)
    print(f"Изображение сохранено: {saved_file}\n")

    # Шаг 6-7: загрузить главную страницу
    print("Загружаю главную страницу...")
    main_html = fetch_page(LIBRARY_URL)
    print("Загружено.\n")

    # Шаг 8: получить ссылки на книги с главной
    book_links = get_all_book_links(main_html)
    print(f"Ссылок на книги (главная): {len(book_links)}\n")

    if book_links:
        # Шаг 9-10: обложка первой книги
        first_html = fetch_page(book_links[0])
        image_url = get_book_image_url(first_html, book_links[0])
        if image_url:
            path = download_image(image_url, OUTPUT_FOLDER)
            print(f"Обложка первой книги: {path}\n")

        # Шаг 11: обложки первых 10 книг
        print("Шаг 11: скачиваю обложки первых 10 книг...")
        for i, url in enumerate(book_links[:10], 1):
            try:
                html = fetch_page(url)
                img_url = get_book_image_url(html, url)
                if img_url:
                    p = download_image(img_url, OUTPUT_FOLDER)
                    print(f"  {i}. + {p}")
                else:
                    print(f"  {i}. - обложка не найдена")
            except Exception as e:
                print(f"  {i}. - ошибка: {e}")

        # Шаг 12-13: информация о первых 5 книгах
        print("\nШаг 12-13: информация о первых 5 книгах...")
        for i, url in enumerate(book_links[:5], 1):
            try:
                html = fetch_page(url)
                info = get_book_info(html)
                print(f"  {i}. {info['title']} | {info['author']} | {info['genre']} | {info['year']}")
            except Exception as e:
                print(f"  {i}. - ошибка: {e}")

        # Шаг 14: текст первой книги
        print("\nШаг 14: скачиваю текст первой книги...")
        try:
            html = fetch_page(book_links[0])
            info = get_book_info(html)
            txt_url = get_book_txt_url(html, book_links[0])
            if txt_url:
                p = download_book_text(txt_url, info["title"])
                print(f"  + {p}")
            else:
                print("  - txt не найден")
        except Exception as e:
            print(f"  - ошибка: {e}")

    # Шаг 15: ссылки на тексты книг из топ-100
    print("\nШаг 15: получаю ссылки на тексты книг из топ-100...")
    top_html = fetch_page(TOP_URL)
    top_links = get_top_book_links(top_html)
    print(f"Книг в топ-100: {len(top_links)}")
    top_txt_urls: list[str] = []
    for book_url in top_links:
        try:
            html = fetch_page(book_url)
            txt_url = get_book_txt_url(html, book_url)
            if txt_url:
                top_txt_urls.append(txt_url)
                print(f"  {txt_url}")
        except Exception as e:
            print(f"  - ошибка ({book_url}): {e}")
    print(f"Получено txt-ссылок: {len(top_txt_urls)}\n")

    # Шаг 16: скачать тексты всех книг топ-100
    print("Шаг 16: скачиваю тексты книг топ-100...")
    for book_url in top_links:
        try:
            html = fetch_page(book_url)
            info = get_book_info(html)
            txt_url = get_book_txt_url(html, book_url)
            if txt_url:
                p = download_book_text(txt_url, info["title"])
                print(f"  + {info['title']}")
            else:
                print(f"  - txt не найден: {book_url}")
        except Exception as e:
            print(f"  - ошибка: {e}")
    print("\nГотово.")


if __name__ == "__main__":
    main()
