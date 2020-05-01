import os
import datetime
import cv2
from pyzbar import pyzbar
from flask import Flask, redirect, render_template, url_for, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kutuphane-uygulamasi'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

KITAP_RESMI_KLASORU = 'static/img/kitap-resimleri'

app.config['KITAP_RESMI_KLASORU'] = KITAP_RESMI_KLASORU

db = SQLAlchemy(app)

kullanici_adi = ""

class Kullanicilar(db.Model):
    kullanici_adi = db.Column(db.String(5),  primary_key=True)
    kullanici_sifre = db.Column(db.String(1))
    ustundeki_kitap_sayisi = db.Column(db.Integer)
    kitap_alabilirmi = db.Column(db.Integer)

    def __repr__(self):
        return f'<Kullanıcı {self.kullanici_adi}>'

class Kitaplar(db.Model):
    kitap_isbn = db.Column(db.String(15), primary_key=True)
    kitap_adi = db.Column(db.String(30))
    kimde = db.Column(db.String(5))
    verilecegi_tarihi = db.Column(db.String(10))
    kr_dosya_adi = db.Column(db.String(30))

    def __repr__(self):
        return f'<Kitap {self.kitap_adi}>'

class Zaman(db.Model):
    zaman_katsayisi = db.Column(db.Integer,primary_key=True)

    def __repr__(self):
        return f'<Zaman Katsayısı: {self.zaman_katsayisi}>'

@app.route("/", methods=['GET', 'POST'])
def anasayfa():
    global kullanici_adi
    kullanici_adi = ""
    if request.form.get('giris') == 'admin':
        if request.form.get('input_admin_adi') == "admin" and request.form.get('input_admin_sifre') == "123":
            kullanici_adi = "admin"
            return redirect('admin_paneli')
    if request.form.get('giris2') == 'kullanici':
        kullanici = Kullanicilar.query.filter_by(kullanici_adi=request.form['input_kullanici_adi']).first()
        if kullanici != None:
            if request.form.get('input_kullanici_sifre') == kullanici.kullanici_sifre:
                kullanici_adi = kullanici.kullanici_adi
                return redirect('kullanici_paneli')
    return render_template('anasayfa.html')

@app.route("/admin_paneli", methods=["GET", "POST"])
def admin_paneli():
    
    kullanicilar = Kullanicilar.query.all()
    for kullanici in kullanicilar:
        kullanici.ustundeki_kitap_sayisi = len(Kitaplar.query.filter_by(kimde=kullanici.kullanici_adi).all())
        
        kullanici.kitap_alabilirmi = "Evet"
        db.session.commit()

        if(kullanici.ustundeki_kitap_sayisi >= 3):
            kullanici.kitap_alabilirmi = "Hayır"
            db.session.commit()

        for ustundeki_kitap in Kitaplar.query.filter_by(kimde=kullanici.kullanici_adi).all():
            verilecegi_zaman_datetime = datetime.datetime.strptime(ustundeki_kitap.verilecegi_tarihi, '%d/%m/%Y').date()
            suanki_tarih = (datetime.datetime.now() + datetime.timedelta(days=Zaman.query.first().zaman_katsayisi)).date()
            if(suanki_tarih > verilecegi_zaman_datetime):
                kullanici.kitap_alabilirmi = "Hayır"
                db.session.commit()
            
    if "input_kitap_resmi" in request.files and "input_isbn_resmi" in request.files and request.form.get('input_kitap_ismi') != "" : 
        kitapIsmi = request.form.get('input_kitap_ismi')
        kitapResmi = request.files["input_kitap_resmi"]
        isbnResmi = request.files["input_isbn_resmi"]

        kitapResmiAdi = secure_filename(kitapResmi.filename)
        isbnResmiAdi = secure_filename(isbnResmi.filename)
    
        kitapResmi.save(os.path.join(app.config['KITAP_RESMI_KLASORU'], "kapak_" + kitapResmiAdi)) 
        isbnResmi.save(os.path.join(app.config['KITAP_RESMI_KLASORU'], "isbn_" + isbnResmiAdi)) 
        
        isbnresmi_yolu = os.path.join(app.config['KITAP_RESMI_KLASORU'], "isbn_" + isbnResmiAdi)
        isbn = barkod_bul(isbnresmi_yolu)

        if(Kitaplar.query.filter_by(kitap_isbn=isbn).first() == None and isbn != None):
            yeni_kitap = Kitaplar(
            kitap_isbn = isbn,
            kitap_adi=kitapIsmi,
            kimde="",
            verilecegi_tarihi="",
            kr_dosya_adi= "kapak_" + kitapResmiAdi
            )
        
            db.session.add(yeni_kitap)
            db.session.commit()
        
        return render_template('adminpaneli.html', kullanici_adi= 'admin', kac_gun_ilerletildi=Zaman.query.first().zaman_katsayisi, kitapIsmi=kitapIsmi, kitapResmi=kitapResmiAdi, isbnResmi=isbnResmiAdi, kullaniciVeritabani=Kullanicilar.query.all(), kitapVeriTabani=Kitaplar.query.all())
    
    else:
        return render_template('adminpaneli.html', kullanici_adi= 'admin', kac_gun_ilerletildi=Zaman.query.first().zaman_katsayisi, kullaniciVeritabani=Kullanicilar.query.all(), kitapVeriTabani=Kitaplar.query.all())
    
@app.route("/zaman_ilerlet", methods=["GET", "POST"])
def zaman_ilerlet():
    Zaman.query.first().zaman_katsayisi += int(request.form.get("ilerletilecek_gun"))
    db.session.commit()
    return redirect(url_for("admin_paneli"))

@app.route("/zaman_sifirla", methods=["GET", "POST"])
def zaman_sifirla():
    Zaman.query.first().zaman_katsayisi = 0
    db.session.commit()
    return redirect(url_for("admin_paneli"))

def barkod_bul(resim_yolu):
    resim = cv2.imread(resim_yolu)

    try:
        barkod_cizgileri = pyzbar.decode(resim)
        barkod_cizgileri = pyzbar.decode(resim)
        barkod_verisi=""
        for cizgi in barkod_cizgileri:
            barkod_verisi = cizgi.data.decode('utf-8')
            return barkod_verisi
    except TypeError:
        return None


@app.route("/kullanici_paneli", methods=["GET", "POST"])
def kullanici_paneli():
    kullanicilar = Kullanicilar.query.all()
    for kullanici in kullanicilar:
        kullanici.ustundeki_kitap_sayisi = len(Kitaplar.query.filter_by(kimde=kullanici.kullanici_adi).all())
        
        kullanici.kitap_alabilirmi = "Evet"
        db.session.commit()

        if(kullanici.ustundeki_kitap_sayisi >= 3):
            kullanici.kitap_alabilirmi = "Hayır"
            db.session.commit()

        for ustundeki_kitap in Kitaplar.query.filter_by(kimde=kullanici.kullanici_adi).all():
            verilecegi_zaman_datetime = datetime.datetime.strptime(ustundeki_kitap.verilecegi_tarihi, '%d/%m/%Y').date()
            suanki_tarih = (datetime.datetime.now() + datetime.timedelta(days=Zaman.query.first().zaman_katsayisi)).date()
            if(suanki_tarih > verilecegi_zaman_datetime):
                kullanici.kitap_alabilirmi = "Hayır"
                db.session.commit()

    kullanici = Kullanicilar.query.filter_by(kullanici_adi=kullanici_adi).first()

    if request.form.get("hangi_kitap_alinacak") != None and request.form.get("verilecegi_tarihi") != None and kullanici.kitap_alabilirmi != "Hayır": 
        alinacak_kitap = Kitaplar.query.filter_by(kitap_isbn=request.form.get("hangi_kitap_alinacak")).first()
        if alinacak_kitap != None and alinacak_kitap.kimde == "":
            alinacak_kitap.kimde = kullanici_adi
            alinacak_kitap.verilecegi_tarihi = request.form.get("verilecegi_tarihi")
            kullanici.ustundeki_kitap_sayisi += 1
            db.session.commit()
            return redirect('kullanici_paneli')
        
    if "input_verilecek_kitap_isbn" in request.files:
        isbnResmi = request.files["input_verilecek_kitap_isbn"]
        isbnResmiAdi = secure_filename(isbnResmi.filename)
        isbnresmi_yolu = os.path.join(app.config['KITAP_RESMI_KLASORU'], "isbn_" + isbnResmiAdi)

        kitap = Kitaplar.query.filter_by(kitap_isbn=barkod_bul(isbnresmi_yolu)).first()
        kullanici = Kullanicilar.query.filter_by(kullanici_adi=kullanici_adi).first()
        if(kitap != None and kitap.kimde == kullanici.kullanici_adi):
            kitap.kimde = ""
            kitap.verilecegi_tarihi = ""
            kullanici.kitap_alabilirmi = "Evet"
            kullanici.ustundeki_kitap_sayisi -= 1
            db.session.commit()
        return redirect(url_for("kullanici_paneli"))

    return render_template('kullanicipaneli.html', kullanici=kullanici, kac_gun_ilerletildi=Zaman.query.first().zaman_katsayisi, kitaplarVeritabani=Kitaplar.query.all(), kullanicilarVeritabani=Kullanicilar.query.all())

@app.route("/kitaplar", methods=["GET", "POST"])
def kitaplar():
    return render_template("kitaplar.html", kitaplarVeritabani=Kitaplar.query.all())

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)