"""Локальное окно в браузере. Картинка обрабатывается только на этом ПК."""
import argparse
import base64
import io
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
from PIL import Image
from kjb import embed, extract, metrics

HTML = '''<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Куттер–Джордан–Боссен</title><style>
body{font:17px Arial;max-width:1000px;margin:35px auto;padding:0 24px;color:#163047;background:#f4f7fa}
h1{font-size:30px}main{background:white;padding:28px;border-radius:12px}label{display:block;margin:12px 0}
input,textarea,button{font:inherit;padding:9px;border:1px solid #bac8d3;border-radius:5px}input[type=number]{width:85px}
textarea{width:95%;height:65px}button{background:#124b7a;color:white;cursor:pointer;margin:10px 8px 10px 0}
.params{display:flex;gap:20px;flex-wrap:wrap}.images{display:flex;gap:16px;flex-wrap:wrap}.images img{max-width:280px;max-height:260px}
pre{white-space:pre-wrap;background:#eaf0f5;padding:14px}small{color:#526778}a{color:#125a98}
</style><main><h1>Скрываем текст в картинке</h1>
<p>Метод Куттера–Джордана–Боссена. Лабораторная работа №2.</p>
<label>Картинка <input id="file" type="file" accept="image/png,image/jpeg,image/bmp"></label>
<div class="params"><label>Ключ<br><input id="key" value="TKI-441"></label>
<label>Сила q<br><input id="q" type="number" value="0.1" min="0.001" max="1" step="0.01"></label>
<label>Повторов<br><input id="n" type="number" value="31" min="1"></label>
<label>Радиус<br><input id="c" type="number" value="3" min="1"></label>
<label>Длина, бит<br><input id="length" type="number" value="56" min="1"></label></div>
<label>Текст для скрытия<textarea id="message">TKI-441</textarea></label>
<button onclick="run('embed')">Спрятать и проверить</button><button onclick="run('extract')">Извлечь из выбранной картинки</button>
<p><small>Для извлечения выберите сохранённый PNG и укажите те же ключ, повторы, радиус и длину сообщения.
Сила q для чтения не нужна. Картинки обрабатываются локально.</small></p>
<p id="download"></p><pre id="result">Выберите картинку. Для первого опыта подойдёт results/gradient/cover.png.</pre>
<div class="images"><div>Исходная<br><img id="before"></div><div>После записи<br><img id="after"></div>
<div>Разница ×8<br><img id="diff"></div></div>
</main><script>
const $=id=>document.getElementById(id);
async function run(action){try{
 const f=$('file').files[0];if(!f)throw Error('Сначала выберите картинку.');
 const image=await new Promise((ok,no)=>{let r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(f)});
 $('before').src=image;$('result').textContent='Вычисляю…';$('download').replaceChildren();
 const payload={action,image,key:$('key').value,q:Number($('q').value),n:Number($('n').value),c:Number($('c').value),length:Number($('length').value),message:$('message').value};
 const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const r=await response.json();if(!response.ok)throw Error(r.error);
 $('result').textContent=r.description;
 if(r.image){$('after').src=r.image;$('diff').src=r.difference;$('length').value=r.length;
 let a=document.createElement('a');a.href=r.image;a.download='stego.png';a.textContent='Скачать заполненную картинку PNG';$('download').append(a);
 }else{$('after').removeAttribute('src');$('diff').removeAttribute('src');}
}catch(e){$('result').textContent='Ошибка: '+e.message}}
</script></html>'''


def png_data(a):
    stream=io.BytesIO()
    Image.fromarray(a).save(stream,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(stream.getvalue()).decode("ascii")


def process(data):
    encoded=data["image"].split(",",1)[1]
    with Image.open(io.BytesIO(base64.b64decode(encoded,validate=True))) as source:
        if source.width*source.height>4_000_000:
            raise ValueError("Для демонстрации используйте картинку до 4 миллионов пикселей.")
        image=np.array(source.convert("RGB"))
    n,c=int(data["n"]),int(data["c"])
    if data["action"]=="embed":
        bits=np.unpackbits(np.frombuffer(data["message"].encode("utf-8"),dtype=np.uint8))
        out,clipped=embed(image,bits,data["key"],float(data["q"]),n,c)
        got,_,_=extract(out,len(bits),data["key"],n,c)
        errors=int(np.count_nonzero(got!=bits))
        m=metrics(image,out)
        psnr='∞' if m['psnr_rgb_db'] is None else f"{m['psnr_rgb_db']:.2f}"
        delta=np.clip(np.abs(out.astype(np.int16)-image.astype(np.int16))*8,0,255).astype(np.uint8)
        return {"image":png_data(out),"difference":png_data(delta),"length":len(bits),
                "description":f"Скрыто битов: {len(bits)}\nОшибок чтения: {errors}; BER = {100*errors/len(bits):.2f}%\n"
                f"MSE = {m['mse_rgb']:.4f}; PSNR = {psnr} дБ\nИзменено пикселей: {m['changed_pixels_percent']:.2f}%\n"
                f"Обрезаний диапазона: {clipped}\nДля чтения: длина {len(bits)}, повторы {n}, радиус {c}."}
    if data["action"]!="extract": raise ValueError("Неизвестное действие.")
    bits,_,threshold=extract(image,int(data["length"]),data["key"],n,c)
    text=np.packbits(bits).tobytes().decode("utf-8",errors="replace") if len(bits)%8==0 else "Не кратно 8 битам"
    return {"description":f"Извлечённый текст:\n{text}\n\nБиты:\n{''.join(map(str,bits))}\n\nПорог: {threshold:.4f}\n"
            "Правильность чтения без исходного сообщения или контрольной суммы не гарантируется."}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def do_POST(self):
        try:
            if self.path!="/api": raise ValueError("Неизвестный путь.")
            origin=self.headers.get('Origin')
            if origin and origin!=f"http://127.0.0.1:{self.server.server_port}":
                raise ValueError("Запрос разрешён только из локального окна программы.")
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=25_000_000: raise ValueError("Размер запроса недопустим.")
            result=process(json.loads(self.rfile.read(length)))
            status=200
        except (ValueError,KeyError,OSError,TypeError) as error:
            status,result=400,{"error":str(error)}
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(result,ensure_ascii=False).encode("utf-8"))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    server=HTTPServer(("127.0.0.1",args.port),Handler)
    print(f"Откройте http://127.0.0.1:{server.server_port}; для выхода Ctrl+C",flush=True)
    if not args.no_browser:
        threading.Timer(.5,lambda:webbrowser.open(f"http://127.0.0.1:{server.server_port}")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
