# -*- coding: utf-8 -*-
"""
Caso 5 — Soluciones intermedias y frontera de Pareto (aproximación).

Metodología: variar el tope de costo z1 <= (1 + epsilon) * z1_min y, para cada epsilon,
maximizar z2 con las mismas reglas del laboratorio (R1, R2).

Ejecutar desde la carpeta caso5 (donde está 'Soporte Caso 5.xlsx'):
    python pareto_intermedias_caso5.py

Requisitos: pandas, pulp, geopy, matplotlib, numpy
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pulp as lp
from geopy.distance import distance
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------------------------------------------------------
# Datos (igual espíritu que el notebook del Caso 5)
# -----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
EXCEL = BASE / "Soporte Caso 5.xlsx"


def cargar_parametros():
    cacs = pd.read_excel(EXCEL, sheet_name="CACs")
    depositos = pd.read_excel(EXCEL, sheet_name="Depositos")

    I = depositos.Municipio.to_list()
    J = cacs.Municipio.to_list()

    capacidad = {row["Municipio"]: row["Capacidad"] for _, row in depositos.iterrows()}
    costo_fijo = {row["Municipio"]: row["CostoFijo"] for _, row in depositos.iterrows()}
    depositos_lat_lon = {
        row["Municipio"]: (row["Latitud"], row["Longitud"])
        for _, row in depositos.iterrows()
    }

    produccion = {row["Municipio"]: row["Produccion"] for _, row in cacs.iterrows()}
    cacs_lat_lon = {
        row["Municipio"]: (row["Latitud"], row["Longitud"]) for _, row in cacs.iterrows()
    }

    q = 90
    r = 125  # km — documento / notebook

    distancia: dict[tuple[str, str], float] = {
        (i, j): float(distance(depositos_lat_lon[i], cacs_lat_lon[j]).kilometers)
        for i in I
        for j in J
    }

    costo_transporte = {
        (i, j): q * produccion[j] * distancia[(i, j)] for i in I for j in J
    }

    return I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte, q, r


def expresion_costo_total(y, x, I, J, costo_fijo, costo_transporte):
    return lp.lpSum(costo_fijo[i] * y[i] for i in I) + lp.lpSum(
        costo_transporte[i, j] * x[i, j] for i in I for j in J
    )


def expresion_satisfaccion(x, J, I, produccion, distancia, r):
    return lp.lpSum(
        produccion[j] * x[i, j]
        for j in J
        for i in I
        if distancia[(i, j)] <= r
    )


def resolver_min_z1(I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte):
    prob = lp.LpProblem(sense=lp.LpMinimize)
    x = lp.LpVariable.dicts("x", [(i, j) for i in I for j in J], cat=lp.LpBinary)
    y = lp.LpVariable.dicts("y", I, cat=lp.LpBinary)

    prob += expresion_costo_total(y, x, I, J, costo_fijo, costo_transporte)
    for j in J:
        prob += lp.lpSum(x[i, j] for i in I) == 1, f"R1_{j}"
    for i in I:
        prob += (
            lp.lpSum(produccion[j] * x[i, j] for j in J) <= capacidad[i] * y[i]
        ), f"R2_{i}"

    status = prob.solve(lp.PULP_CBC_CMD(msg=False))
    if lp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Min z1: estado {lp.LpStatus[status]}")

    z1_opt = float(lp.value(prob.objective))
    r_ = 125
    z2_post = float(
        lp.value(
            expresion_satisfaccion(
                x, J, I, produccion, distancia, r_
            )
        )
    )
    return z1_opt, z2_post


def resolver_max_z2_sin_tope(I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte, r):
    prob = lp.LpProblem(sense=lp.LpMaximize)
    x = lp.LpVariable.dicts("x", [(i, j) for i in I for j in J], cat=lp.LpBinary)
    y = lp.LpVariable.dicts("y", I, cat=lp.LpBinary)

    prob += expresion_satisfaccion(x, J, I, produccion, distancia, r)
    for j in J:
        prob += lp.lpSum(x[i, j] for i in I) == 1, f"R1_{j}"
    for i in I:
        prob += (
            lp.lpSum(produccion[j] * x[i, j] for j in J) <= capacidad[i] * y[i]
        ), f"R2_{i}"

    status = prob.solve(lp.PULP_CBC_CMD(msg=False))
    if lp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Max z2: estado {lp.LpStatus[status]}")

    z2_opt = float(lp.value(prob.objective))
    z1_post = float(lp.value(expresion_costo_total(y, x, I, J, costo_fijo, costo_transporte)))
    return z1_post, z2_opt


def resolver_max_z2_con_tope_costo(
    I,
    J,
    capacidad,
    costo_fijo,
    produccion,
    distancia,
    costo_transporte,
    r: float,
    z1_max: float,
):
    """Maximiza z2 con z1 <= z1_max (restricción tipo R3 del laboratorio)."""
    prob = lp.LpProblem(sense=lp.LpMaximize)
    x = lp.LpVariable.dicts("x", [(i, j) for i in I for j in J], cat=lp.LpBinary)
    y = lp.LpVariable.dicts("y", I, cat=lp.LpBinary)

    prob += expresion_satisfaccion(x, J, I, produccion, distancia, r)
    for j in J:
        prob += lp.lpSum(x[i, j] for i in I) == 1, f"R1_{j}"
    for i in I:
        prob += (
            lp.lpSum(produccion[j] * x[i, j] for j in J) <= capacidad[i] * y[i]
        ), f"R2_{i}"

    costo_expr = expresion_costo_total(y, x, I, J, costo_fijo, costo_transporte)
    prob += costo_expr <= z1_max, "R3_costo_max"

    status = prob.solve(lp.PULP_CBC_CMD(msg=False))
    if lp.LpStatus[status] != "Optimal":
        return None, None, lp.LpStatus[status]

    z2v = float(lp.value(prob.objective))
    z1v = float(lp.value(costo_expr))
    return z1v, z2v, lp.LpStatus[status]


def main():
    I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte, q, r = (
        cargar_parametros()
    )

    print("1) Mínimo costo z1* y z2 asociado")
    z1_min, z2_at_min = resolver_min_z1(
        I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte
    )
    print(f"   z1* = {z1_min:,.2f}  |  z2 (medida) = {z2_at_min:,.2f}")

    print("\n2) Máximo z2 sin tope de costo (extremo servicio)")
    z1_at_maxz2, z2_max = resolver_max_z2_sin_tope(
        I, J, capacidad, costo_fijo, produccion, distancia, costo_transporte, r
    )
    print(f"   z1 = {z1_at_maxz2:,.2f}  |  z2 = {z2_max:,.2f}")

    # Barrido de soluciones intermedias: epsilon sobre el mejor costo
    epsilons = np.linspace(0.0, 0.15, 16)  # 0 % … 15 % sobre z1*
    z1_pts: list[float] = []
    z2_pts: list[float] = []
    eps_pts: list[float] = []
    status_pts: list[str] = []

    print("\n3) Intermedias: max z2 con z1 <= (1+eps)*z1*")
    for eps in epsilons:
        cap = z1_min * (1.0 + float(eps))
        z1v, z2v, st = resolver_max_z2_con_tope_costo(
            I,
            J,
            capacidad,
            costo_fijo,
            produccion,
            distancia,
            costo_transporte,
            r,
            cap,
        )
        if z1v is None:
            print(f"   eps={100*eps:.1f}%  tope={cap:,.2f}  -> {st}")
            continue
        z1_pts.append(z1v)
        z2_pts.append(z2v)
        eps_pts.append(eps)
        status_pts.append(st)
        print(
            f"   eps={100*eps:5.1f}%  tope={cap:,.2f}  -> z1={z1v:,.2f}  z2={z2v:,.2f}"
        )

    prod_total = sum(produccion.values())

    # Gráfico tipo "frontera": costo vs satisfacción
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(z1_pts, z2_pts, c="steelblue", s=55, zorder=3, label="Intermedias (ε-restricción)")

    # Extremos de referencia
    ax.scatter([z1_min], [z2_at_min], c="green", s=120, marker="*", zorder=4, label="Min z1")
    ax.scatter([z1_at_maxz2], [z2_max], c="darkorange", s=120, marker="D", zorder=4, label="Max z2 (sin tope)")

    # Línea guía ordenando por z1
    order = np.argsort(z1_pts)
    z1s = np.array(z1_pts)[order]
    z2s = np.array(z2_pts)[order]
    ax.plot(z1s, z2s, color="steelblue", alpha=0.5, linewidth=1.5, label="Aprox. frontera")

    ax.set_xlabel("Costo total z1 (operación + transporte)")
    ax.set_ylabel("Satisfacción z2 (producción ≤ r km, miles de ton ponderadas)")
    ax.set_title("Caso 5 — Compromiso costo vs servicio (aprox. frente de Pareto)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")

    fig2, ax2 = plt.subplots(figsize=(9, 5.5))
    z1_arr = np.array(z1_pts)
    z2_arr = np.array(z2_pts)
    pct_costo = 100.0 * z1_arr / z1_min
    pct_z2 = 100.0 * z2_arr / prod_total
    ax2.scatter(pct_costo, pct_z2, c="steelblue", s=55, zorder=3)
    o = np.argsort(z1_arr)
    ax2.plot(pct_costo[o], pct_z2[o], color="steelblue", alpha=0.5)
    ax2.axvline(102.0, color="red", linestyle="--", alpha=0.7, label="+2 % vs z1* (ej. lab)")
    ax2.set_xlabel("% costo relativo al mínimo (100% = z1*)")
    ax2.set_ylabel("% satisfacción z2 / producción total")
    ax2.set_title("Misma frontera en porcentajes (útil para presentar)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    out = BASE / "pareto_caso5.png"
    out2 = BASE / "pareto_caso5_porcentajes.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    fig2.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close("all")
    print(f"\nGráficos guardados:\n  {out}\n  {out2}")

    # Criterio de recomendación automático (ejemplo): máximo z2 con tope +2 %
    cap_2pct = z1_min * 1.02
    z1_rec, z2_rec, st_rec = resolver_max_z2_con_tope_costo(
        I,
        J,
        capacidad,
        costo_fijo,
        produccion,
        distancia,
        costo_transporte,
        r,
        cap_2pct,
    )
    print("\n4) Ejemplo de recomendación (criterio: no pasar +2 % del costo mínimo)")
    if st_rec == "Optimal" and z1_rec is not None:
        print(f"   Tope z1 <= {cap_2pct:,.2f}")
        print(f"   Solución recomendada: z1 = {z1_rec:,.2f}  |  z2 = {z2_rec:,.2f}")
        print(
            f"   Costo relativo: {100*z1_rec/z1_min:.2f}%  |  "
            f"z2 / producción total: {100*z2_rec/prod_total:.2f}%"
        )
    else:
        print(f"   No se obtuvo óptimo: {st_rec}")


if __name__ == "__main__":
    main()
