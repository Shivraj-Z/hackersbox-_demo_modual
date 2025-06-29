# modules/password_checker.py
import hashlib
import requests
import string

def check_strength(password):
    length = len(password)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in string.punctuation for c in password)
    score = sum([has_upper, has_lower, has_digit, has_symbol]) + (length >= 8)
    if score == 5:
        return "Strong"
    elif score >= 3:
        return "Medium"
    else:
        return "Weak"

def check_pwned(password):
    sha1_pw = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1_pw[:5], sha1_pw[5:]
    try:
        res = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
        if res.status_code != 200:
            return -1
        hashes = (line.split(':') for line in res.text.splitlines())
        for h, count in hashes:
            if h == suffix:
                return int(count)
        return 0
    except Exception:
        return -1


# modules/vuln_scanner.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def get_forms(url):
    try:
        soup = BeautifulSoup(requests.get(url).text, "html.parser")
        return soup.find_all("form")
    except:
        return []

def form_details(form):
    details = {"action": form.attrs.get("action"), "method": form.attrs.get("method", "get").lower(), "inputs": []}
    for tag in form.find_all("input"):
        input_type = tag.attrs.get("type", "text")
        name = tag.attrs.get("name")
        details["inputs"].append({"type": input_type, "name": name})
    return details

def test_xss(url):
    forms = get_forms(url)
    js_script = "<script>alert('XSS')</script>"
    vulnerable = []
    for form in forms:
        details = form_details(form)
        data = {inp['name']: js_script for inp in details['inputs'] if inp['type'] == 'text' and inp['name']}
        form_url = urljoin(url, details['action'])
        if details['method'] == "post":
            res = requests.post(form_url, data=data)
        else:
            res = requests.get(form_url, params=data)
        if js_script in res.text:
            vulnerable.append(form_url)
    return vulnerable

def test_sqli(url):
    payloads = ["'", "' OR 1=1 --", "' OR 'a'='a"]
    errors = ["sql syntax", "mysql", "syntax error", "unclosed"]
    for payload in payloads:
        res = requests.get(f"{url}?id={payload}")
        if any(e in res.text.lower() for e in errors):
            return payload
    return None

def scan_directories(url, wordlist):
    found = []
    try:
        with open(wordlist, 'r') as f:
            for path in f:
                full_url = f"{url}/{path.strip()}"
                res = requests.get(full_url)
                if res.status_code == 200:
                    found.append(full_url)
    except:
        return []
    return found


# modules/phishing_detector.py
import joblib
import re
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'phishing_model.pkl')
model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None

def extract_features(url):
    return [
        len(url),
        url.count('@'),
        url.count('//'),
        re.search(r'https?://', url) is None,
        url.count('-'),
        url.count('.')
    ]

def check_url(url):
    if model is None:
        return "Model not loaded"
    features = extract_features(url)
    prediction = model.predict([features])[0]
    return "Phishing" if prediction == 1 else "Legitimate"


# modules/steganography.py
from PIL import Image

def encode_image(image_path, message, output_path):
    img = Image.open(image_path)
    encoded = img.copy()
    width, height = img.size
    message += "###"
    data = iter(message.encode())
    for y in range(height):
        for x in range(width):
            pixel = list(img.getpixel((x, y)))
            for n in range(3):
                try:
                    val = next(data)
                    pixel[n] = (pixel[n] & ~1) | (val & 1)
                except StopIteration:
                    encoded.putpixel((x, y), tuple(pixel))
                    encoded.save(output_path)
                    return True
            encoded.putpixel((x, y), tuple(pixel))
    return False

def decode_image(image_path):
    img = Image.open(image_path)
    binary = ''
    for y in range(img.height):
        for x in range(img.width):
            for n in img.getpixel((x, y))[:3]:
                binary += str(n & 1)
    chars = [chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8)]
    message = ''.join(chars)
    return message.split("###")[0]
