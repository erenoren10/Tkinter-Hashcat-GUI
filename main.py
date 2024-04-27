import subprocess
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import re
import secrets


secilen_dosya_yolu = None

def baslat():
    durum_etiketi.config(text="İşlem başlatıldı...", fg="black")
    pencere.after(100, metni_gonder)




def metni_gonder():
    girilen_metin = entry.get()
    girilen_yol = path_entry.get()
    hash_dosya_yol = hash_dosya_entry.get()
    word_dosya_yol = wordlist_dosya_entry.get()
    global secilen_dosya_yolu

    if not girilen_metin or not girilen_yol:
        durum_etiketi.config(text="Parametleri Girin!", fg="red")
        return

    klasor_yolu = girilen_yol
    komut = f'echo {girilen_metin}  {hash_dosya_yol}  {word_dosya_yol} --force | cmd'

    dosya_adi = "hashcat_cikti_" + datetime.now().strftime("%d-%m-%Y;%H;%M;%S") + ".txt"
    process = subprocess.run(komut, shell=True, capture_output=True, cwd=klasor_yolu)

    try:
        stdout_str = process.stdout.decode('utf-8')
    except UnicodeDecodeError:
        stdout_str = process.stdout.decode('cp1254', errors='replace')

    stdout_str = stdout_str.replace('\ufffd', '')

    sha1_deseni = r'sha1\$[0-9a-f]+\$.+'
    sha1_satirlari = re.findall(sha1_deseni, stdout_str)

    if len(sha1_satirlari) > 0:
        try:
            baglanti = sqlite3.connect('veritabani.db')
            cursor = baglanti.cursor()

            for satir in sha1_satirlari:
                parcalar = satir.strip().split(':')
                hash_degeri = parcalar[0]
                password = parcalar[1].strip()

                cursor.execute('''
                    SELECT * FROM veriler WHERE hash=?
                ''', (hash_degeri,))

                row = cursor.fetchone()

                if row:
                    cursor.execute('''
                        UPDATE veriler SET password=? WHERE hash=?
                    ''', (password, hash_degeri))

            baglanti.commit()
        except Exception as e:
            print("Veritabanı işlemlerinde bir hata oluştu:", e)
        finally:
            baglanti.close()


    veriler = dosya_oku(secilen_dosya_yolu)

    sonuclar = []

    for satir in veriler:
        parcalar = satir.strip().split(':')
        phone_number = parcalar[1].strip()
        baglanti = sqlite3.connect('veritabani.db')
        cursor = baglanti.cursor()
        cursor.execute("SELECT hash,phone_number,password FROM veriler WHERE phone_number=?", (phone_number,))
        sonuclar.extend(cursor.fetchall())
        baglanti.close()

    with open(dosya_adi, "w", encoding="utf-8") as dosya:
            for satir in sonuclar:
                dosya.write(":".join(str(s) for s in satir if s is not None) + "\n")

    durum_etiketi.config(text="İşlem başarıyla tamamlandı!", fg="green")



def store_db(giris_dosyasi):
    try:
        baglanti = sqlite3.connect('veritabani.db')
        cursor = baglanti.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS veriler (
                id INTEGER PRIMARY KEY,
                hash TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                password TEXT,
                code TEXT,
                create_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        baglanti.commit()
        print("Veritabanı ve tablo başarıyla oluşturuldu.")
    except Exception as e:
        print("Veritabanı oluşturulurken bir hata oluştu:", e)
    finally:
        baglanti.close()

    veriler = dosya_oku(giris_dosyasi)
    toplam_satir = len(veriler)
    basarili = 0

    def db_ekle(index=0):
        nonlocal basarili

        try:

            batch_size = 100
            end_index = min(index + batch_size, toplam_satir)

            for i in range(index, end_index):
                code = secrets.token_hex(4)
                satir = veriler[i]
                parcalar = satir.strip().split(':')
                if len(parcalar) >= 2:
                    hash_degeri = parcalar[0]
                    phone_number = parcalar[1].strip()

                    try:
                        baglanti = sqlite3.connect('veritabani.db')
                        cursor = baglanti.cursor()

                        cursor.execute('''
                                                    SELECT * FROM veriler WHERE hash=? AND phone_number=?
                                                ''', (hash_degeri, phone_number))

                        if not cursor.fetchall():
                            cursor.execute('''
                                                        INSERT INTO veriler (hash, phone_number, code)
                                                        VALUES (?, ?, ?)
                                                    ''', (hash_degeri, phone_number, code))

                        baglanti.commit()
                        basarili += 1
                    except Exception as e:
                        print("Veri eklenirken bir hata oluştu:", e)
                    finally:
                        baglanti.close()

            ilerleme = int((end_index / toplam_satir) * 100)
            sonuc_label.config(text=f" Şifre Bilgileri veri tabanına ekleniyor - İlerleme: %{ilerleme}")

            if end_index < toplam_satir:
                pencere.after(100, db_ekle, end_index)
            else:
                sonuc_label.config(text=f"İşlem tamamlandı, Başarılı: {basarili}/{toplam_satir}")
        except Exception as e:
            sonuc_label.config(text="Hata: " + str(e))

    pencere.after(100, db_ekle)


def dosya_oku(giris_dosyasi):
    with open(giris_dosyasi, "r", encoding="utf-8") as dosya:
        veriler = dosya.readlines()
    return veriler


def dosya_sec(metin_degiskeni):
    giris_dosyasi = filedialog.askopenfilename(filetypes=[("Metin Dosyaları", "*.txt")])
    global secilen_dosya_yolu
    secilen_dosya_yolu = giris_dosyasi

    if giris_dosyasi:
        cikis_dosyasi = giris_dosyasi.split('.')[0] + "_cikti.txt"
        kripto_kir(giris_dosyasi, cikis_dosyasi)
        metin_degiskeni.delete(0, tk.END)
        metin_degiskeni.insert(0, cikis_dosyasi)
        store_db(giris_dosyasi)
        secilen_dosya_yolu = giris_dosyasi

def kripto_kir(giris_dosyasi, cikis_dosyasi):
    try:
        def cozme_islemi():
            try:
                with open(giris_dosyasi, 'r', encoding='utf-8') as dosya:
                    with open(cikis_dosyasi, 'w', encoding='utf-8') as cikis:
                        for satir in dosya:
                            parcalar = satir.strip().split(':')
                            if parcalar:
                                cikis.write(parcalar[0] + '\n')
                sonuc_label.config(text="Hashler çözülecek hale geldi. yolu: " + cikis_dosyasi)
            except Exception as e:
                sonuc_label.config(text="Hata: " + str(e))
                print(e)

        pencere.after(100, cozme_islemi)
    except Exception as e:
        sonuc_label.config(text="Hata: " + str(e))


def dosya_sec_word(metin_degiskeni):
    dosya_yolu = filedialog.askopenfilename(filetypes=[("Metin Dosyaları", "*.txt")])
    if dosya_yolu:
        metin_degiskeni.delete(0, tk.END)
        metin_degiskeni.insert(0, dosya_yolu)


pencere = tk.Tk()
pencere.title("Hashcat Uygulaması")

etiket_yol = tk.Label(pencere, text="Hashcat Yolunu Girin: (C:/Path/../../folder/hashcat-6.2.6)")
etiket_yol.grid(row=0, column=0, pady=5, padx=5, sticky='w')
path_entry = tk.Entry(pencere, width=50)
path_entry.grid(row=0, column=1, pady=5, padx=5, sticky='w')

etiket_metin = tk.Label(pencere, text="Hashcat Parametrelerini Girin: (hashcat.exe -a 0 -m 124...)")
etiket_metin.grid(row=1, column=0, pady=5, padx=5, sticky='w')
entry = tk.Entry(pencere, width=50)
entry.grid(row=1, column=1, pady=5, padx=5, sticky='w')

dosya_sec_metin1 = tk.Label(pencere, text="Kırılacak Hash Dosyasını Seçin:")
dosya_sec_metin1.grid(row=2, column=0, pady=5, padx=5, sticky='w')
hash_dosya_entry = tk.Entry(pencere, width=50 , state='readonly')
hash_dosya_entry.insert(0, "Mevcut değer buraya gelecek")
hash_dosya_entry.grid(row=2, column=1, pady=5, padx=5, sticky='w')
dosya_sec_button1 = ttk.Button(pencere, text="Hash Seç", command=lambda: dosya_sec(hash_dosya_entry))
dosya_sec_button1.grid(row=2, column=2, pady=5, padx=5, sticky='w')

dosya_sec_metin2 = tk.Label(pencere, text="Wordlist Dosyasını Seçin:")
dosya_sec_metin2.grid(row=3, column=0, pady=5, padx=5, sticky='w')
wordlist_dosya_entry = tk.Entry(pencere, width=50)
wordlist_dosya_entry.grid(row=3, column=1, pady=5, padx=5, sticky='w')
dosya_sec_button2 = ttk.Button(pencere, text="Wordlist Seç", command=lambda: dosya_sec_word(wordlist_dosya_entry))
dosya_sec_button2.grid(row=3, column=2, pady=5, padx=5, sticky='w')

gonder_buton = ttk.Button(pencere, text="Başlat", command=baslat)
gonder_buton.grid(row=4, column=0, pady=10, padx=5, sticky='w')

sonuc_label = tk.Label(pencere, text="", font=("Arial", 8))
sonuc_label.grid(row=5, column=0, columnspan=3, pady=10, padx=5, sticky='w')

durum_etiketi = tk.Label(pencere, text="", font=("Arial", 12))
durum_etiketi.grid(row=6, column=0, columnspan=3, pady=5, padx=5, sticky='w')

pencere.mainloop()
