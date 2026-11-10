"""Letreiramento e retoque das paginas de FIADOR.

Le a arte crua gerada (sem texto) em arte/bruto/pXX.png, converte para P&B,
aplica retoques e desenha baloes, recordatorios, onomatopeias e titulo.
Saida: paginas/pagina_XX.png

Uso: python3 tools/letreiramento.py [pagina ...]
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(RAIZ, "tools", "fontes")
BRUTO = os.path.join(RAIZ, "arte", "bruto")
SAIDA = os.path.join(RAIZ, "paginas")

F_FALA = os.path.join(FONTES, "ComicNeue-Bold.ttf")
F_NARRA = os.path.join(FONTES, "ComicNeue-BoldItalic.ttf")
F_SFX = os.path.join(FONTES, "Bangers.ttf")
F_TITULO = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_SUB = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
F_DOC = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"
F_PLACA = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

PRETO = (12, 12, 12)
BRANCO = (255, 255, 255)
SS = 2  # supersampling das formas


def fonte(caminho, tam):
    return ImageFont.truetype(caminho, tam)


# ---------------------------------------------------------------- base

def preparar(caminho):
    """P&B + niveis: papel branco, pretos densos, sem tinta colorida."""
    im = Image.open(caminho).convert("L")
    im = im.point(lambda v: max(0, min(255, round((v - 6) * 255 / (236 - 6)))))
    return im.convert("RGB")


# ---------------------------------------------------------------- texto

def medir_bloco(linhas, f, entre):
    d = ImageDraw.Draw(Image.new("L", (8, 8)))
    larg = []
    alt_linha = f.getbbox("ÁÇgjp")[3] - f.getbbox("ÁÇgjp")[1]
    for ln in linhas:
        b = d.textbbox((0, 0), ln, font=f)
        larg.append(b[2] - b[0])
    h = alt_linha * len(linhas) + entre * (len(linhas) - 1)
    return max(larg), h, larg, alt_linha


def escrever_centro(draw, cx, cy, linhas, f, entre, cor=PRETO, stroke=0, stroke_cor=BRANCO):
    w, h, larg, alt = medir_bloco(linhas, f, entre)
    y = cy - h / 2
    asc_ajuste = f.getbbox("ÁÇgjp")[1]
    for ln, lw in zip(linhas, larg):
        draw.text((cx - lw / 2, y - asc_ajuste), ln, font=f, fill=cor,
                  stroke_width=stroke, stroke_fill=stroke_cor)
        y += alt + entre


# ---------------------------------------------------------------- formas

def _colar_forma(page, mascara, origem, contorno):
    """mascara (L, em SS) -> borda preta + miolo branco colados na pagina."""
    lw = contorno * SS
    tam = lw * 2 + 1
    borda = mascara.filter(ImageFilter.MaxFilter(tam if tam % 2 else tam + 1))
    w, h = mascara.size
    borda = borda.resize((w // SS, h // SS), Image.LANCZOS)
    miolo = mascara.resize((w // SS, h // SS), Image.LANCZOS)
    page.paste(PRETO, origem, borda)
    page.paste(BRANCO, origem, miolo)


def _cauda_pts(cx, cy, a, b, tx, ty, abertura=0.20, curva=0.18):
    ang = math.atan2((ty - cy) / b, (tx - cx) / a)
    p1 = (cx + a * 0.80 * math.cos(ang - abertura), cy + b * 0.80 * math.sin(ang - abertura))
    p2 = (cx + a * 0.80 * math.cos(ang + abertura), cy + b * 0.80 * math.sin(ang + abertura))
    # curva leve: ponto de controle deslocado perpendicularmente
    mx, my = (p1[0] + tx) / 2, (p1[1] + ty) / 2
    nx, ny = -(ty - p1[1]), (tx - p1[0])
    n = math.hypot(nx, ny) or 1
    k = curva * math.hypot(tx - p1[0], ty - p1[1])
    c1 = (mx + nx / n * k, my + ny / n * k)
    mx2, my2 = (p2[0] + tx) / 2, (p2[1] + ty) / 2
    c2 = (mx2 + nx / n * k * 0.6, my2 + ny / n * k * 0.6)

    def bez(p0, c, p3, passos=14):
        return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p3[0],
                 (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p3[1])
                for t in [i / passos for i in range(passos + 1)]]

    ida = bez(p1, c1, (tx, ty))
    volta = list(reversed(bez(p2, c2, (tx, ty))))
    return ida + volta


def balao(page, cx, cy, texto, cauda=None, tam=36, entre=6, folga=(1.22, 1.30),
          pad=22, contorno=3, minw=0):
    """Balao de fala eliptico com texto em CAIXA ALTA centralizado."""
    f = fonte(F_FALA, tam)
    linhas = texto.upper().split("\n")
    w, h, _, _ = medir_bloco(linhas, f, entre)
    w = max(w, minw)
    a = w / 2 * folga[0] + pad
    b = h / 2 * folga[1] + pad
    pontos = [(cx - a, cy - b), (cx + a, cy + b)]
    if cauda:
        pontos.append(cauda)
    x0 = int(min(p[0] for p in pontos)) - 12
    y0 = int(min(p[1] for p in pontos)) - 12
    x1 = int(max(p[0] for p in pontos)) + 12
    y1 = int(max(p[1] for p in pontos)) + 12
    m = Image.new("L", ((x1 - x0) * SS, (y1 - y0) * SS), 0)
    dm = ImageDraw.Draw(m)
    lx, ly = (cx - x0) * SS, (cy - y0) * SS
    dm.ellipse([lx - a * SS, ly - b * SS, lx + a * SS, ly + b * SS], fill=255)
    if cauda:
        pts = _cauda_pts(lx, ly, a * SS, b * SS, (cauda[0] - x0) * SS, (cauda[1] - y0) * SS)
        dm.polygon(pts, fill=255)
    _colar_forma(page, m, (x0, y0), contorno)
    escrever_centro(ImageDraw.Draw(page), cx, cy + 1, linhas, f, entre)


def grito(page, cx, cy, texto, tam=40, raio=(150, 90), pontas=18, contorno=3, cauda=None):
    """Balao espinhoso (susto / grito)."""
    f = fonte(F_FALA, tam)
    linhas = texto.upper().split("\n")
    a, b = raio
    x0, y0 = int(cx - a * 1.3) - 10, int(cy - b * 1.3) - 10
    x1, y1 = int(cx + a * 1.3) + 10, int(cy + b * 1.3) + 10
    m = Image.new("L", ((x1 - x0) * SS, (y1 - y0) * SS), 0)
    dm = ImageDraw.Draw(m)
    pts = []
    for i in range(pontas * 2):
        t = math.pi * 2 * i / (pontas * 2)
        r = 1.28 if i % 2 == 0 else 0.92
        pts.append(((cx - x0 + a * r * math.cos(t)) * SS, (cy - y0 + b * r * math.sin(t)) * SS))
    dm.polygon(pts, fill=255)
    _colar_forma(page, m, (x0, y0), contorno)
    escrever_centro(ImageDraw.Draw(page), cx, cy, linhas, f, 4)


def recordatorio(page, x, y, texto, tam=31, larg=None, pad=(18, 14), contorno=3,
                 alinhar="centro", entre=6, inverso=False):
    """Caixa de narracao retangular. (x, y) = canto superior esquerdo."""
    f = fonte(F_NARRA, tam)
    linhas = texto.split("\n")
    w, h, larg_l, alt = medir_bloco(linhas, f, entre)
    W = int((larg or w) + pad[0] * 2)
    H = int(h + pad[1] * 2)
    d = ImageDraw.Draw(page)
    fundo, tinta = (PRETO, BRANCO) if inverso else (BRANCO, PRETO)
    d.rectangle([x, y, x + W, y + H], fill=PRETO)
    d.rectangle([x + contorno, y + contorno, x + W - contorno, y + H - contorno], fill=fundo)
    asc = f.getbbox("ÁÇgjp")[1]
    yy = y + pad[1]
    for ln, lw in zip(linhas, larg_l):
        xx = x + pad[0] if alinhar == "esq" else x + (W - lw) / 2
        d.text((xx, yy - asc), ln, font=f, fill=tinta)
        yy += alt + entre
    return W, H


def sfx(page, cx, cy, texto, tam=150, angulo=0, contorno=10, cor=PRETO, borda=BRANCO,
        fonte_sfx=F_SFX, espaco=0):
    """Onomatopeia com contorno, rotacionada."""
    f = fonte(fonte_sfx, tam)
    d0 = ImageDraw.Draw(Image.new("L", (8, 8)))
    larg = sum(d0.textlength(c, font=f) for c in texto) + espaco * (len(texto) - 1)
    W, H = int(larg + contorno * 4 + 20), int(tam * 1.4 + contorno * 4)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    x = contorno * 2 + 10
    for c in texto:
        d.text((x, contorno * 2), c, font=f, fill=cor + (255,), stroke_width=contorno,
               stroke_fill=borda + (255,))
        x += d.textlength(c, font=f) + espaco
    camada = camada.rotate(angulo, resample=Image.BICUBIC, expand=True)
    page.paste(camada, (int(cx - camada.width / 2), int(cy - camada.height / 2)), camada)


def texto_rotacionado(page, x, y, linhas, f, angulo, cor=(25, 25, 25), entre=10, cisalha=0.0,
                      fundo_alpha=None):
    """Bloco de texto (ex.: documento) com rotacao e cisalhamento horizontal."""
    alt = f.getbbox("ÁÇgjp")[3] - f.getbbox("ÁÇgjp")[1]
    d0 = ImageDraw.Draw(Image.new("L", (8, 8)))
    W = int(max(d0.textlength(l, font=f) for l in linhas)) + 40
    H = int((alt + entre) * len(linhas)) + 40
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    yy = 20
    asc = f.getbbox("ÁÇgjp")[1]
    for ln in linhas:
        d.text((20, yy - asc), ln, font=f, fill=cor + (255,))
        yy += alt + entre
    if cisalha:
        camada = camada.transform((W + int(abs(cisalha) * H), H), Image.AFFINE,
                                  (1, cisalha, -abs(cisalha) * H if cisalha > 0 else 0, 0, 1, 0),
                                  resample=Image.BICUBIC)
    camada = camada.rotate(angulo, resample=Image.BICUBIC, expand=True)
    page.paste(camada, (int(x), int(y)), camada)


def limpar_texto_falso(page, pontos, poupar=(), limiar=190, abertura=11, folga=5):
    """Pinta de branco o 'texto falso' dentro do poligono 'pontos'. Manchas
    escuras grandes (dedos, unhas) sao detectadas por abertura morfologica e
    preservadas; tracos finos (letras) sao apagados."""
    xs = [p[0] for p in pontos]
    ys = [p[1] for p in pontos]
    x0, y0, x1, y1 = min(xs) - 20, min(ys) - 20, max(xs) + 20, max(ys) + 20
    reg = page.crop((x0, y0, x1, y1)).convert("L")
    escuro = reg.point(lambda v: 255 if v < limiar else 0)
    bolhas = escuro.filter(ImageFilter.MinFilter(abertura)).filter(ImageFilter.MaxFilter(abertura))
    bolhas = bolhas.filter(ImageFilter.MaxFilter(folga * 2 + 1))
    alvo = Image.new("L", reg.size, 0)
    da = ImageDraw.Draw(alvo)
    da.polygon([(x - x0, y - y0) for x, y in pontos], fill=255)
    for (a, b, c, d) in poupar:
        da.rectangle([a - x0, b - y0, c - x0, d - y0], fill=0)
    alvo.paste(0, (0, 0), bolhas)
    alvo = alvo.filter(ImageFilter.GaussianBlur(0.8))
    page.paste(BRANCO, (x0, y0), alvo)


def numero_pagina(page, n):
    f = fonte(F_SUB, 26)
    d = ImageDraw.Draw(page)
    t = str(n)
    w = d.textlength(t, font=f)
    d.text(((page.width - w) / 2, page.height - 52), t, font=f, fill=(90, 90, 90))


# ================================================================ paginas

def pagina_1(p):
    # --- retoque: placa com ideogramas -> placa em portugues
    d = ImageDraw.Draw(p)
    d.rectangle([548, 633, 718, 673], fill=(214, 214, 214))
    d.rectangle([548, 633, 718, 673], outline=(60, 60, 60), width=2)
    f = fonte(F_PLACA, 30)
    t = "CHAVEIRO"
    d.text((633 - d.textlength(t, font=f) / 2, 636), t, font=f, fill=(45, 45, 45))

    # --- retoque: texto falso do contrato -> contrato real
    limpar_texto_falso(p, [(352, 1190), (622, 1190), (612, 1300), (600, 1440),
                           (570, 1478), (450, 1488), (320, 1500), (232, 1506),
                           (234, 1470), (250, 1420), (272, 1376), (300, 1338),
                           (350, 1300)],
                       poupar=[(328, 1490, 562, 1602)])
    doc = fonte(F_DOC, 16)
    texto_rotacionado(p, 268, 1162, [
        "CONTRATO DE FIANÇA Nº 0013",
        "",
        "DEVEDOR: (vide anexo)",
        "FIADOR:  BENEDITO SARAIVA",
        "VALOR:   R$ 4.700.000,00",
        "",
        "O FIADOR assume, em caráter",
        "irrevogável, a dívida acima,",
        "renunciando ao benefício",
        "de ordem.",
    ], doc, angulo=-3.0, entre=9, cisalha=0.36)

    # --- titulo
    sfx(p, 470, 190, "FIADOR", tam=150, contorno=9, cor=BRANCO, borda=PRETO,
        fonte_sfx=F_TITULO, espaco=14)
    recordatorio(p, 168, 282, "Capítulo 1 — Firma Reconhecida", tam=30, inverso=True,
                 pad=(20, 10))
    recordatorio(p, 1270, 112, "Centro de São Paulo.\n23h47.", tam=30)

    # --- painel 2
    recordatorio(p, 718, 990, "Dizem que a assinatura\né a coisa mais pessoal\nque alguém tem.", tam=29)
    # --- painel 3
    recordatorio(p, 452, 975, "Bobagem.\nAssinatura é\nsó um desenho.", tam=29)
    recordatorio(p, 92, 1595, "E todo desenho\npode ser copiado.", tam=29)
    # --- painel 4
    balao(p, 1390, 1920, "Quatro milhões\ne setecentos mil...", cauda=(1080, 2080), tam=35)
    balao(p, 1000, 1880, "A assinatura\né minha...", cauda=(820, 2050), tam=35)
    balao(p, 1330, 2180, "...mas eu nunca\nassinei isso.", cauda=(920, 2200), tam=35)


def pagina_2(p):
    recordatorio(p, 742, 140, "Ninguém assina\nigual duas vezes.", tam=29)
    recordatorio(p, 480, 600, "A mão cansa.\nA tinta falha.\nO humor muda.", tam=29)
    recordatorio(p, 1150, 830, "Mas a deste contrato é\nidêntica à do meu RG.", tam=29)
    recordatorio(p, 1290, 1445, "Traço por traço.", tam=29)
    balao(p, 1080, 1680, "Isso não foi\nassinado...", cauda=(1320, 1830), tam=35)
    balao(p, 1110, 2190, "Foi\ncopiado.", cauda=(1240, 2140), tam=38)
    recordatorio(p, 520, 1600, "Só duas pessoas\nno mundo copiam\numa firma assim.", tam=29)
    recordatorio(p, 104, 2005, "Eu...\ne o meu pai.", tam=29)
    recordatorio(p, 586, 2235, "Que morreu\nhá três anos.", tam=29)


def pagina_3(p):
    # --- retoque: painel 1 regerado (Dito estava de jaqueta; agora camisa branca)
    painel = preparar(os.path.join(BRUTO, "p3_painel1_corrigido.png"))
    p.paste(painel, (102, 104))
    sfx(p, 1035, 195, "TLIM", tam=110, angulo=8, contorno=8, espaco=4)
    balao(p, 1095, 640, "Benedito\nSaraiva?", cauda=(1270, 810), tam=35)
    balao(p, 640, 640, "Sou escrevente\ndo 13º Tabelionato\nde Notas.", cauda=(520, 770), tam=31)
    balao(p, 250, 790, "Vim tratar da\nsua fiança.", cauda=(420, 860), tam=31)
    balao(p, 520, 1290, "Eu não\nassinei nada.", cauda=(690, 1380), tam=31)
    balao(p, 400, 1540, "Assinou, sim.", cauda=(270, 1500), tam=31)
    balao(p, 520, 1690, "E nós reconhecemos\na firma.", cauda=(300, 1620), tam=31)
    sfx(p, 950, 2035, "TAC!", tam=190, angulo=-6, contorno=12, espaco=6)


def pagina_4(p):
    balao(p, 960, 290, "Não existe\n13º Tabelionato\nem São Paulo.", cauda=(1150, 420), tam=34)
    balao(p, 200, 230, "Existe.", cauda=(250, 345), tam=36)
    balao(p, 560, 960, "Só abre à\nmeia-noite.", cauda=(470, 830), tam=34)
    balao(p, 1290, 1240, "Esta noite, seis fiadores\nvão disputar seis dívidas\nque não são deles.",
          cauda=(980, 1330), tam=30)
    balao(p, 420, 1260, "Quem sair com\na firma limpa...\nsai livre.", cauda=(380, 1370), tam=30)
    balao(p, 1400, 1760, "E quem sair\ncom as dívidas?", cauda=(1320, 1900), tam=33)
    balao(p, 200, 1760, "Paga.", cauda=(300, 1880), tam=40)
    balao(p, 790, 2250, "Com o que\ntiver.", cauda=(640, 2140), tam=34)


def pagina_5(p):
    recordatorio(p, 122, 130, "13º Tabelionato de Notas.\n00h00.", tam=30)
    balao(p, 1330, 1050, "Sejam bem-vindos,\nsenhores fiadores.", cauda=(1000, 1170), tam=32)
    balao(p, 390, 1110, "A regra é uma só:\nao amanhecer, cada dívida\nterá um único fiador.",
          cauda=(770, 1200), tam=29)
    balao(p, 1300, 1330, "Convençam alguém a assinar\nno lugar de vocês.", cauda=(990, 1230), tam=28)
    balao(p, 1290, 1600, "Gostou da sua\nassinatura,\nBenedito?", cauda=(1180, 1830), tam=33)
    balao(p, 1430, 2260, "Levei três anos\npara acertar\no traço.", cauda=(1340, 2120), tam=33)
    grito(p, 640, 1600, "...!", tam=46, raio=(70, 50))
    recordatorio(p, 104, 2290, "Continua...", tam=30, inverso=True)


PAGINAS = {1: pagina_1, 2: pagina_2, 3: pagina_3, 4: pagina_4, 5: pagina_5}


def main(nums):
    os.makedirs(SAIDA, exist_ok=True)
    for n in nums:
        p = preparar(os.path.join(BRUTO, f"p{n}.png"))
        PAGINAS[n](p)
        numero_pagina(p, n)
        p = p.convert("L")
        destino = os.path.join(SAIDA, f"pagina_{n:02d}.png")
        p.save(destino, optimize=True)
        print("ok", destino, p.size)
    montar_extras()


def montar_extras():
    """PDF do capitulo + folha com as 5 paginas (ordem de leitura: direita -> esquerda)."""
    pgs = [Image.open(os.path.join(SAIDA, f"pagina_{n:02d}.png")).convert("L")
           for n in sorted(PAGINAS)]
    pdf = os.path.join(SAIDA, "FIADOR_capitulo_01.pdf")
    pgs[0].save(pdf, save_all=True, append_images=pgs[1:], resolution=200)
    w, h = pgs[0].size
    tw, th, gap = w // 4, h // 4, 24
    folha = Image.new("L", (tw * len(pgs) + gap * (len(pgs) + 1), th + gap * 2), 255)
    for i, pg in enumerate(pgs):
        x = gap + (len(pgs) - 1 - i) * (tw + gap)
        folha.paste(pg.resize((tw, th), Image.LANCZOS), (x, gap))
    folha.save(os.path.join(SAIDA, "visao_geral.png"), optimize=True)
    print("ok", pdf)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5])
