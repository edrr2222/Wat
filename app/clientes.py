"""
Configuración de clientes (multi-tenant)
---------------------------------------------------------
Cada cliente se define con un bloque corto. El prompt del
sistema y el saludo inicial se arman automáticamente a partir
de estos datos — no hay que escribir un prompt largo a mano
por cada cliente nuevo.

Para agregar un cliente nuevo (otro parque, un restaurante,
un hospital, lo que sea):
  1. Crea una carpeta en app/conocimiento/<id_cliente>/
  2. Suelta ahí sus documentos en Markdown (.md)
  3. Agrega un bloque aquí abajo con su información
  4. Cambia CLIENTE_ACTIVO en tu .env al id_cliente nuevo
"""

CLIENTES = {
    "jaime_duque": {
        "nombre": "Parque Jaime Duque",
        "tipo_negocio": "parque temático de naturaleza, cultura e historia",
        "descripcion_corta": (
            "Ubicado en Tocancipá, Cundinamarca, a 45 minutos de Bogotá. "
            "Combina zoológico, museos, reservas naturales y atracciones "
            "históricas en 200 hectáreas."
        ),
        "carpeta_conocimiento": "jaime_duque",
        "emoji": "🌳",
        "usa_clima": True,  # útil porque muchas atracciones son al aire libre
        "sugerencias": [
            "¿Cuáles son los horarios y tarifas?",
            "¿Qué atracciones hay para niños?",
            "¿Cómo llego desde Bogotá?",
            "¿Va a llover hoy en Tocancipá?",
        ],
    },
    "restaurante_ejemplo": {
        "nombre": "Restaurante Ejemplo",
        "tipo_negocio": "restaurante de cocina colombiana contemporánea",
        "descripcion_corta": "Ubicado en Chapinero, Bogotá. Cliente de demostración.",
        "carpeta_conocimiento": "restaurante_ejemplo",
        "emoji": "🍽️",
        "usa_clima": False,  # no aporta valor para un restaurante
        "sugerencias": [
            "¿Cuál es el horario?",
            "¿Tienen platos vegetarianos?",
            "¿Cómo reservo para un grupo grande?",
        ],
    },
}


def obtener_cliente(cliente_id: str) -> dict:
    if cliente_id not in CLIENTES:
        disponibles = ", ".join(CLIENTES.keys())
        raise ValueError(f"Cliente '{cliente_id}' no configurado. Disponibles: {disponibles}")
    return CLIENTES[cliente_id]
