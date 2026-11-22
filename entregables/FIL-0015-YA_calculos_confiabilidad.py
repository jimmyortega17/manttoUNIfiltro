"""
Cálculos de confiabilidad del filtro prensa FIL-0015-YA (tesis Indigoyen, v15).
Uso:  python FIL-0015-YA_calculos_confiabilidad.py [archivo.xlsx] [--rapido]
      Sin archivo, busca en la carpeta actual cualquier .xlsx con una hoja "Datos" (sirve aunque el nombre tenga "(1)").
      --rapido: 60 réplicas por prueba en lugar de 300/500 (unos 20 segundos); útil para verificar que todo corre.
      Los valores publicados en la tesis corresponden a la ejecución completa (sin --rapido), de unos 2 minutos.
      Resultados de referencia de la ejecución completa: resultados_confiabilidad_referencia.json.
Entrada: hoja "Datos" (552 registros del Reporte Diario MMP, 01/01/2025-13/11/2026). Sirve el respaldo
         FIL-0015-YA_Respaldo_Tesis_v15.xlsx (predeterminado) o el Excel CORREGIDO original: ambos tienen la misma hoja Datos.
Tiempo de ejecución aproximado: 1,5 minutos.

Definiciones de método:
- Tiempo entre fallas (TBF): horas desde el fin de un evento de falla hasta el inicio del siguiente, descontando TODAS
  las paradas registradas del equipo en ese lapso. Para los subsistemas se usa la misma regla: un subsistema solo
  acumula tiempo de funcionamiento cuando el filtro está en marcha, por lo que se descuentan también las paradas
  originadas en otros subsistemas (riesgos en competencia; la falla de otro subsistema no reinicia el reloj).
- Censura: el intervalo desde la última falla de cada año hasta el cierre del periodo es censurado por la derecha.
  El intervalo desde el inicio del periodo hasta la primera falla se excluye, porque se desconoce la edad del
  equipo en ese momento (truncamiento por la izquierda).
- Horizonte de simulación del bootstrap: la suma de los intervalos observados (completos + censurado), que es el
  tiempo de funcionamiento acumulado entre la primera falla y el cierre del periodo. Como los intervalos ya están
  expresados en tiempo de funcionamiento (sin paradas), simular una secuencia de fallas en ese horizonte reproduce
  el mecanismo de observación real: cada réplica termina con un intervalo censurado, igual que los datos.
Salida: resultados por consola y resultados_confiabilidad.json.
Probado con Python 3.13, numpy 2.5, scipy 1.18, openpyxl 3.1. Semillas aleatorias fijas (ver SEMILLAS).
"""
import sys, json, datetime as dt, numpy as np, openpyxl
from scipy import stats, optimize
SEMILLAS = dict(ks_censura=31, ad_censura=21, ad_equipo_weibull=1, ad_subsistemas_weibull=1, ad_subsistemas_otras=2, ad_modelos_equipo=3, jitter=11)
FALLA = ('CPRO', 'REAC', 'ACCI')                       # clases que cuentan como falla (OPER excluido)
INICIO = {2025: dt.datetime(2025, 1, 1), 2026: dt.datetime(2026, 1, 1)}
CIERRE = {2025: dt.datetime(2026, 1, 1), 2026: dt.datetime(2026, 11, 14)}

def leer(path):
    ws = openpyxl.load_workbook(path)['Datos']; R = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] is None: continue
        per, yr, f, h, _, _, _, tipo, _, dem, _, _, par, sub = r[:14]
        isp = par == 'SI'
        R.append(dict(per=per, yr=yr, start=dt.datetime.combine(f.date(), h), dem=float(dem or 0), tipo=tipo, sub=sub,
                      isp=isp, isf=isp and tipo in FALLA and sub != 'Logística / apoyo'))
    return sorted(R, key=lambda d: d['start'])

def union_paradas(R):
    iv = sorted((r['start'], r['start'] + dt.timedelta(hours=r['dem'])) for r in R if r['isp']); U = []
    for a, b in iv:
        if U and a <= U[-1][1]: U[-1][1] = max(U[-1][1], b)
        else: U.append([a, b])
    return U

def tiempo_en_servicio(U, a, b):
    down = sum(max(0, (min(b, y) - max(a, x)).total_seconds() / 3600) for x, y in U)
    return (b - a).total_seconds() / 3600 - down

def eventos(fallas):
    """Agrupa fallas que empiezan mientras el equipo sigue detenido por otra falla."""
    ev = []
    for r in fallas:
        e = r['start'] + dt.timedelta(hours=r['dem'])
        if ev and r['start'] < ev[-1][1]: ev[-1][1] = max(ev[-1][1], e)
        else: ev.append([r['start'], e, r['sub']])
    return ev

def intervalos(U, fallas, cierre):
    ev = eventos(fallas)
    t = np.array([tiempo_en_servicio(U, ev[k-1][1], ev[k][0]) for k in range(1, len(ev))])
    return ev, t[t > 0], tiempo_en_servicio(U, ev[-1][1], cierre)

def weibull_mle(t, c):
    t = np.asarray(t, float); d = 1 - np.asarray(c)
    nll = lambda p: -(np.sum(d * (p[0] - p[1] + (np.exp(p[0]) - 1) * np.log(t / np.exp(p[1])))) - np.sum((t / np.exp(p[1])) ** np.exp(p[0])))
    o = optimize.minimize(nll, [0, np.log(t.mean())], method='Nelder-Mead', options=dict(xatol=1e-9, fatol=1e-9, maxiter=5000))
    return np.exp(o.x[0]), np.exp(o.x[1]), -o.fun

def exp_ll(t, c):
    t = np.asarray(t, float); d = 1 - np.asarray(c); lam = d.sum() / t.sum(); return d.sum() * np.log(lam) - lam * t.sum()

def ad(x, cdf):
    x = np.sort(x); n = len(x); F = np.clip(cdf(x), 1e-12, 1 - 1e-12); i = np.arange(1, n + 1)
    return -n - np.mean((2 * i - 1) * (np.log(F) + np.log(1 - F[::-1])))

MODELOS = {
    'Weibull': (lambda v: weibull_mle(v, np.zeros(len(v)))[:2], lambda v, p: 1 - np.exp(-(v / p[1]) ** p[0]), lambda r, p, n: p[1] * r.weibull(p[0], n)),
    'Exponencial': (lambda v: (v.mean(),), lambda v, p: 1 - np.exp(-v / p[0]), lambda r, p, n: r.exponential(p[0], n)),
    'Lognormal': (lambda v: (np.log(v).mean(), np.log(v).std()), lambda v, p: stats.norm.cdf((np.log(v) - p[0]) / p[1]), lambda r, p, n: np.exp(r.normal(p[0], p[1], n))),
    'Gamma': (lambda v: (lambda a: (a[0], a[2]))(stats.gamma.fit(v, floc=0)), lambda v, p: stats.gamma.cdf(v, p[0], scale=p[1]), lambda r, p, n: r.gamma(p[0], p[1], n)),
}
def ad_bootstrap(x, modelo, B, semilla):
    fit, cdf, gen = MODELOS[modelo]; r = np.random.default_rng(semilla); p = fit(x); A = ad(x, lambda v: cdf(v, p)); c = 0
    for _ in range(B):
        y = gen(r, p, len(x)); q = fit(y); c += ad(y, lambda v: cdf(v, q)) >= A
    return A, (c + 1) / (B + 1)


# ---- Prueba de Anderson-Darling con censura: MLE con censura y bootstrap que reproduce el mecanismo de observación
def mle(dist,t,c):
    t=np.asarray(t,float); d=1-np.asarray(c)
    if dist=='Weibull':
        lp=lambda p,x: stats.weibull_min.logpdf(x,np.exp(p[0]),scale=np.exp(p[1])); ls=lambda p,x: stats.weibull_min.logsf(x,np.exp(p[0]),scale=np.exp(p[1])); x0=[0,np.log(t.mean())]
    elif dist=='Lognormal':
        lp=lambda p,x: stats.lognorm.logpdf(x,np.exp(p[1]),scale=np.exp(p[0])); ls=lambda p,x: stats.lognorm.logsf(x,np.exp(p[1]),scale=np.exp(p[0])); x0=[np.log(t).mean(),np.log(np.log(t).std())]
    elif dist=='Exponencial':
        lp=lambda p,x: stats.expon.logpdf(x,scale=np.exp(p[0])); ls=lambda p,x: stats.expon.logsf(x,scale=np.exp(p[0])); x0=[np.log(t.mean())]
    else:
        lp=lambda p,x: stats.gamma.logpdf(x,np.exp(p[0]),scale=np.exp(p[1])); ls=lambda p,x: stats.gamma.logsf(x,np.exp(p[0]),scale=np.exp(p[1])); x0=[0,np.log(t.mean())]
    nll=lambda p:-(np.sum(lp(p,t[d==1]))+np.sum(ls(p,t[d==0])))
    o=optimize.minimize(nll,x0,method='Nelder-Mead',options=dict(xatol=1e-8,fatol=1e-8,maxiter=4000))
    return o.x
def cdf(dist,p,x):
    if dist=='Weibull': return stats.weibull_min.cdf(x,np.exp(p[0]),scale=np.exp(p[1]))
    if dist=='Lognormal': return stats.lognorm.cdf(x,np.exp(p[1]),scale=np.exp(p[0]))
    if dist=='Exponencial': return stats.expon.cdf(x,scale=np.exp(p[0]))
    return stats.gamma.cdf(x,np.exp(p[0]),scale=np.exp(p[1]))
def rvs(dist,p,n,r):
    if dist=='Weibull': return np.exp(p[1])*r.weibull(np.exp(p[0]),n)
    if dist=='Lognormal': return np.exp(r.normal(p[0],np.exp(p[1]),n))
    if dist=='Exponencial': return r.exponential(np.exp(p[0]),n)
    return r.gamma(np.exp(p[0]),np.exp(p[1]),n)
def simulate(dist,p,L,r):
    out=[]; s=0
    while True:
        x=rvs(dist,p,64,r)
        for v in x:
            if s+v>=L: out.append((L-s,1)); return np.array(out)
            out.append((v,0)); s+=v
def stat(dist,t,c):
    p=mle(dist,t,c); x=t[c==0]; return ad(x,lambda v:cdf(dist,p,v)),p

def ad_censura(T, C, dist, B=300, semilla=21):
    A, p = stat(dist, T, C); r = np.random.default_rng(semilla); L = T.sum(); c = 0
    for _ in range(B):
        s = simulate(dist, p, L, r); a, _ = stat(dist, s[:, 0], s[:, 1].astype(int)); c += a >= A
    return A, (c + 1) / (B + 1)

def ks_censura(T, C, dist, B=300, semilla=31):
    """Distancia máxima entre Kaplan-Meier (con el intervalo censurado) y la distribución ajustada con censura; p por bootstrap con el mismo mecanismo de observación."""
    def D(T_, C_):
        p = mle(dist, T_, C_); km = kaplan_meier(T_, C_); xs = np.array([a for a, _ in km]); S = np.array([b for _, b in km])
        Sm = 1 - cdf(dist, p, xs); Sp = np.concatenate([[1], S[:-1]]); return max(np.abs(S - Sm).max(), np.abs(Sp - Sm).max()), p
    d0, p = D(T, C); r = np.random.default_rng(semilla); L = T.sum(); c = 0
    for _ in range(B):
        s = simulate(dist, p, L, r); c += D(s[:, 0], s[:, 1].astype(int))[0] >= d0
    return d0, (c + 1) / (B + 1)

def kaplan_meier(t, c):
    o = np.argsort(t); t = np.asarray(t)[o]; c = np.asarray(c)[o]; n = len(t); S = 1; out = []; i = 0
    while i < n:
        j = i; d = 0
        while j < n and t[j] == t[i]: d += 1 - c[j]; j += 1
        S *= 1 - d / (n - i); out.append((float(t[i]), S)); i = j
    return out
def S_en(km, h): return ([s for tt, s in km if tt <= h] or [1])[-1]

RAPIDO = '--rapido' in sys.argv
def B_(n): return 60 if RAPIDO else n
def paso(msg): print('>>', msg, flush=True)

def buscar_entrada():
    import glob
    cands = sorted(glob.glob('*.xlsx'), key=lambda f: ('Respaldo' not in f, f))
    for f in cands:
        try:
            if 'Datos' in openpyxl.load_workbook(f, read_only=True).sheetnames: return f
        except Exception: pass
    raise SystemExit('No se encontró un .xlsx con hoja "Datos" en la carpeta actual; indique el archivo como argumento.')

def main(path):
    paso(f'Leyendo {path}' + (' (modo rápido)' if RAPIDO else ''))
    R = leer(path); U = union_paradas(R); res = {}
    for y in (2025, 2026):
        paso(f'Equipo completo {y}: ajuste, Kaplan-Meier y pruebas bootstrap')
        fl = [r for r in R if r['isf'] and r['yr'] == y]
        ev, t, cens = intervalos(U, fl, CIERRE[y])
        tt = np.append(t, cens); cc = np.append(np.zeros(len(t)), 1)
        b, e, ll = weibull_mle(tt, cc); pLR = 1 - stats.chi2.cdf(2 * (ll - exp_ll(tt, cc)), 1)
        km = kaplan_meier(tt, cc)
        mod = {m: dict(zip(('AD', 'p'), ad_bootstrap(t, m, B_(500), SEMILLAS['ad_modelos_equipo']))) for m in MODELOS}
        cens_ad = {m_: dict(zip(('AD', 'p'), ad_censura(tt, cc.astype(int), m_, B_(300), SEMILLAS['ad_censura']))) for m_ in ('Weibull', 'Exponencial', 'Lognormal', 'Gamma')}
        print('   AD con censura:', {k: (round(v['AD'], 2), round(v['p'], 3)) for k, v in cens_ad.items()})
        ks_c = {m_: dict(zip(('D', 'p'), ks_censura(tt, cc.astype(int), m_, B_(300), SEMILLAS['ks_censura']))) for m_ in ('Weibull', 'Exponencial', 'Lognormal', 'Gamma')}
        print('   KS con censura:', {k: (round(v['D'], 3), round(v['p'], 3)) for k, v in ks_c.items()})
        res[y] = dict(ks_con_censura=ks_c, ad_con_censura=cens_ad, fallas=len(fl), eventos=len(ev), intervalos=len(t), censurado_h=cens, tbf_medio=t.mean(),
                      beta=b, eta=e, p_beta_1=pLR, KM={h: S_en(km, h) for h in (24, 48, 72)}, modelos=mod)
        print(y, {k: v for k, v in res[y].items() if k not in ('modelos', 'ad_con_censura', 'ks_con_censura')}); print('   AD:', {m: (round(v['AD'], 2), round(v['p'], 3)) for m, v in mod.items()})
    subs = {}
    for r in R:
        if r['isf']: subs.setdefault(r['sub'], []).append(r)
    res['subsistemas'] = {}
    paso('Subsistemas: Weibull y pruebas de bondad de ajuste')
    for s in ['Tela filtrante', 'Mangueras y conexiones de placas', 'Rodillos y accionamiento de tela', 'Agua de prensado y lavado', 'Diafragmas y sellos de placas', 'Paquete de placas y bastidor']:
        ev, t, cens = intervalos(U, subs[s], CIERRE[2026])
        b, e, ll = weibull_mle(np.append(t, cens), np.append(np.zeros(len(t)), 1))
        pLR = 1 - stats.chi2.cdf(2 * (ll - exp_ll(np.append(t, cens), np.append(np.zeros(len(t)), 1))), 1)
        A, p = ad_bootstrap(t, 'Weibull', B_(300), SEMILLAS['ad_subsistemas_weibull'])
        Ae, pe = ad_bootstrap(t, 'Exponencial', B_(300), SEMILLAS['ad_subsistemas_otras'])
        Al, pl = ad_bootstrap(t, 'Lognormal', B_(300), SEMILLAS['ad_subsistemas_otras'])
        res['subsistemas'][s] = dict(n=len(t), tbf_medio=t.mean(), beta=b, eta=e, AD=A, p=p, AD_exp=Ae, p_exp=pe, AD_logn=Al, p_logn=pl, p_beta_1=pLR)
        print(s, {k: round(v, 3) for k, v in res['subsistemas'][s].items()})
    # Supuestos de Kaplan-Meier: independencia (Spearman entre intervalos consecutivos) y tendencia (prueba de Laplace)
    # Aplicabilidad: fallas repetidas en el mismo subsistema antes de 48 h de funcionamiento desde la reparación anterior
    res['supuestos'] = {}
    for y in (2025, 2026):
        fl = [r for r in R if r['isf'] and r['yr'] == y]; ev, t, cens = intervalos(U, fl, CIERRE[y])
        L = t.sum() + cens; n = len(t); Ulap = (np.cumsum(t).mean() - L / 2) / (L * np.sqrt(1 / (12 * n)))
        rho, prho = stats.spearmanr(t[:-1], t[1:])
        ultimo = {}; h48 = 0.0; n48 = 0
        for r in fl:
            s_ = r['sub']
            if s_ in ultimo and r['start'] > ultimo[s_] and tiempo_en_servicio(U, ultimo[s_], r['start']) <= 48: h48 += r['dem']; n48 += 1
            elif s_ in ultimo and r['start'] <= ultimo[s_]: h48 += r['dem']; n48 += 1
            ultimo[s_] = r['start'] + dt.timedelta(hours=r['dem'])
        res['supuestos'][y] = dict(laplace=Ulap, p_laplace=2 * (1 - stats.norm.cdf(abs(Ulap))), rho1=rho, p_rho1=prho, fallas_repetidas=n48, horas_repetidas=h48)
        print(y, 'supuestos:', {k: round(float(v), 3) for k, v in res['supuestos'][y].items()})
    salida = 'resultados_confiabilidad_rapido.json' if RAPIDO else 'resultados_confiabilidad.json'
    json.dump(res, open(salida, 'w'), indent=1, default=float); paso(f'Listo: {salida}')

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0] if args else buscar_entrada())
