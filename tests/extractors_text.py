"""Texto de relleno que varía en cada llamada (en un libro real las líneas no se repiten)."""

SENT = ("Era una tarde tranquila número {i} en el pueblo y nadie esperaba que llegase el forastero con su "
        "maleta gris, que traía noticias importantes de la ciudad lejana. ")
_seed = [0]


def para(n=3):
    """Texto distinto en cada llamada (en un libro real las líneas no se repiten página tras página)."""
    out = []
    for _ in range(n):
        _seed[0] += 1
        out.append(SENT.format(i=_seed[0]))
    return "".join(out).strip()
