from __future__ import annotations


def apply_contract_hours_heatmap_support(source: str) -> str:
    """Mejora únicamente la presentación del mapa empleado-semana.

    La transformación reutiliza los campos ya calculados por ``weekly_hours``:
    no modifica contratos, desviaciones, ausencias ni estados de planificación.
    """

    old_help = 'help_text("Rojo significa déficit, blanco coincidencia y ámbar exceso. Un ✓ identifica una desviación total o parcialmente explicable por ausencias.")'
    new_help = 'help_text("Rojo significa déficit, blanco coincidencia y ámbar exceso. Un ✓ identifica una desviación total o parcialmente explicable por ausencias. El nuevo filtro puede neutralizar visualmente, sin alterar los datos, los déficits que la ausencia podría explicar por completo.")'
    if old_help not in source:
        raise ValueError("No se encontró el texto de ayuda del mapa semanal")
    source = source.replace(old_help, new_help, 1)

    old_controls = '''    only_deviations = st.checkbox("Mostrar solo empleados con alguna desviacion", value=True, key="weekly_heatmap_deviations")
    pivot = detail.pivot_table(index="Empleado", columns="Semana", values="desviacion_horas", aggfunc="first").reindex(columns=summary["Semana"].tolist())
    if only_deviations:
        pivot = pivot.loc[pivot.abs().max(axis=1).gt(0.01)]
'''
    new_controls = '''    filter_cols = st.columns(2)
    only_deviations = filter_cols[0].checkbox("Mostrar solo empleados con alguna desviacion", value=True, key="weekly_heatmap_deviations")
    neutralize_absence = filter_cols[1].checkbox("Neutralizar déficits totalmente explicables por ausencias", value=False, key="weekly_heatmap_neutralize_absence")
    pivot = detail.pivot_table(index="Empleado", columns="Semana", values="desviacion_horas", aggfunc="first").reindex(columns=summary["Semana"].tolist())
    # El filtro de empleados se evalúa sobre la desviación original. Así, activar
    # la neutralización nunca elimina una fila por sí mismo: solo cambia celdas.
    if only_deviations:
        pivot = pivot.loc[pivot.abs().max(axis=1).gt(0.01)]
    fully_explainable = set(zip(
        detail.loc[detail["posible_explicacion_por_ausencia"].eq("PODRIA EXPLICAR TODAS LAS HORAS FALTANTES"), "Empleado"],
        detail.loc[detail["posible_explicacion_por_ausencia"].eq("PODRIA EXPLICAR TODAS LAS HORAS FALTANTES"), "Semana"],
    ))
    if neutralize_absence and not pivot.empty:
        for employee_key, week_key in fully_explainable:
            if employee_key in pivot.index and week_key in pivot.columns:
                value = pivot.loc[employee_key, week_key]
                if pd.notna(value) and value < -0.01:
                    pivot.loc[employee_key, week_key] = 0.0
'''
    if old_controls not in source:
        raise ValueError("No se encontró el bloque de filtros del mapa semanal")
    source = source.replace(old_controls, new_controls, 1)

    old_text = '''        explainable = set(zip(detail.loc[detail["posible_explicacion_por_ausencia"].astype(str).str.contains("PODRIA EXPLICAR", case=False, na=False), "Empleado"], detail.loc[detail["posible_explicacion_por_ausencia"].astype(str).str.contains("PODRIA EXPLICAR", case=False, na=False), "Semana"]))
        text = [["" if pd.isna(value) else f"{value:+.1f}{' ✓' if (pivot.index[i], pivot.columns[j]) in explainable else ''}" for j, value in enumerate(row)] for i, row in enumerate(pivot.to_numpy())]
        fig = go.Figure(go.Heatmap(z=pivot.to_numpy(), x=pivot.columns, y=pivot.index, zmin=-max_abs, zmax=max_abs, zmid=0, colorscale=[[0, "#b91c1c"], [0.5, "#f8fafc"], [1, "#d97706"]], text=text, texttemplate="%{text}", colorbar={"title": "Desviacion h"}, hovertemplate="%{y}<br>%{x}<br>%{z:+.1f} h<extra></extra>"))
'''
    new_text = '''        explainable = set(zip(detail.loc[detail["posible_explicacion_por_ausencia"].astype(str).str.contains("PODRIA EXPLICAR", case=False, na=False), "Empleado"], detail.loc[detail["posible_explicacion_por_ausencia"].astype(str).str.contains("PODRIA EXPLICAR", case=False, na=False), "Semana"]))
        text = [["" if pd.isna(value) else ("0" if neutralize_absence and (pivot.index[i], pivot.columns[j]) in fully_explainable and abs(value) <= 0.01 else f"{value:+.1f}{' ✓' if (pivot.index[i], pivot.columns[j]) in explainable else ''}") for j, value in enumerate(row)] for i, row in enumerate(pivot.to_numpy())]

        contract_labels = {}
        for employee_key, employee_rows in detail.sort_values(["ano_iso", "semana_iso"]).groupby("Empleado", sort=False):
            values = []
            for contract_value in employee_rows["applicableWorkingHours"]:
                if pd.isna(contract_value):
                    continue
                numeric_value = float(contract_value)
                if not values or abs(values[-1] - numeric_value) > 0.01:
                    values.append(numeric_value)
            if values:
                contract_text = " → ".join(f"{value:g}" for value in values) + " h"
                contract_labels[employee_key] = f"{employee_key} · {contract_text}"
            else:
                contract_labels[employee_key] = f"{employee_key} · — h"
        employee_labels = [contract_labels.get(employee_key, employee_key) for employee_key in pivot.index]

        week_starts = detail.drop_duplicates("Semana").set_index("Semana")["inicio_semana"]
        week_labels = [pd.to_datetime(week_starts.loc[week_key]).strftime("%d/%m/%Y") if week_key in week_starts.index else str(week_key) for week_key in pivot.columns]

        fig = go.Figure(go.Heatmap(z=pivot.to_numpy(), x=week_labels, y=employee_labels, zmin=-max_abs, zmax=max_abs, zmid=0, colorscale=[[0, "#b91c1c"], [0.5, "#f8fafc"], [1, "#d97706"]], text=text, texttemplate="%{text}", colorbar={"title": "Desviacion h"}, hovertemplate="%{y}<br>Semana desde %{x}<br>%{z:+.1f} h<extra></extra>"))
'''
    if old_text not in source:
        raise ValueError("No se encontró la construcción del heatmap semanal")
    source = source.replace(old_text, new_text, 1)
    return source
