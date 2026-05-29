import streamlit as st
import mysql.connector
import re

def validar_dni_nie(documento):
    
    documento = documento.strip().upper()
    patron_dni = r'^\d{8}[A-Z]$'
    patron_nie = r'^[XYZ]\d{7}[A-Z]$'
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    if re.match(patron_dni, documento):
        numero = int(documento[:8])
        letra = documento[-1]
        letra_correcta = letras[numero % 23]
        return letra == letra_correcta
    elif re.match(patron_nie, documento):
        equivalencias = {
            "X": "0",
            "Y": "1",
            "Z": "2"
        }
        numero_nie = (
            equivalencias[documento[0]]
            + documento[1:8]
        )
        numero = int(numero_nie)
        letra = documento[-1]
        letra_correcta = letras[numero % 23]
        return letra == letra_correcta
    return False
conexion = mysql.connector.connect(
    host=st.secrets["MYSQL_HOST"],
    port=st.secrets["MYSQL_PORT"],
    user=st.secrets["MYSQL_USER"],
    password=st.secrets["MYSQL_PASSWORD"],
    database=st.secrets["MYSQL_DATABASE"]
)
cursor = conexion.cursor(buffered=True)

def texto(valor):
    return "" if valor is None else str(valor)

def cargar_widgets_desde_session_state():
    roles_validos = ["Debatiente", "Capitán", "Suplente"]
    version_carga = st.session_state.get("version_carga", 0)

    st.session_state[f"select_profesores_{version_carga}"] = max(
        1,
        min(len(st.session_state.profesores), 3)
    )
    st.session_state[f"select_equipos_{version_carga}"] = max(
        1,
        min(len(st.session_state.equipos), 6)
    )

    for i, profesor in enumerate(st.session_state.profesores):
        st.session_state[f"profesor_modificar_{version_carga}_{i}"] = texto(profesor.get("nombre"))
        st.session_state[f"dni_profesor_modificar_{version_carga}_{i}"] = texto(profesor.get("dni"))
        st.session_state[f"telefono_profesor_modificar_{version_carga}_{i}"] = texto(profesor.get("telefono"))
        st.session_state[f"correo_profesor_modificar_{version_carga}_{i}"] = texto(profesor.get("correo"))

    for i, equipo in enumerate(st.session_state.equipos):
        miembros = equipo.get("miembros", [])
        st.session_state[f"equipo_modificar_{version_carga}_{i}"] = texto(equipo.get("nombre_equipo"))
        st.session_state[f"num_miembros_{version_carga}_{i}"] = max(1, min(len(miembros), 6))

        for j, miembro in enumerate(miembros):
            rol = miembro.get("rol", "Debatiente")
            if rol not in roles_validos:
                rol = "Debatiente"

            st.session_state[f"nombre_modificar_{version_carga}_{i}_{j}"] = texto(miembro.get("nombre"))
            st.session_state[f"dni_modificar_{version_carga}_{i}_{j}"] = texto(miembro.get("dni"))
            st.session_state[f"curso_modificar_{version_carga}_{i}_{j}"] = texto(miembro.get("curso"))
            st.session_state[f"mail_modificar_{version_carga}_{i}_{j}"] = texto(miembro.get("mail"))
            st.session_state[f"rol_modificar_{version_carga}_{i}_{j}"] = rol

col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("logo.png", width=200)
st.title("Sistema de Inscripción de Torneos")
modo = st.radio(
    "¿Qué deseas hacer?",
    [
        "Nueva inscripción",
        "Modificar inscripción"
    ],
    key="modo"
)

if "datos_centro" not in st.session_state:
    st.session_state.datos_centro = None
if "profesores" not in st.session_state:
    st.session_state.profesores = []
if "equipos" not in st.session_state:
    st.session_state.equipos = []
if "version_carga" not in st.session_state:
    st.session_state.version_carga = 0

if modo == "Modificar inscripción":

    correo_busqueda = st.text_input(
        "Correo electrónico del centro"
    )

    if st.button("Cargar inscripción"):

        cursor.execute("""
            SELECT *
            FROM centros
            WHERE correo = %s
            ORDER BY id DESC
            LIMIT 1
        """, (correo_busqueda,))

        resultado = cursor.fetchone()

        if resultado:
            st.session_state.modo = "Modificar inscripción"
            st.session_state.datos_centro = resultado
            centro_id = resultado[0]
            cursor.execute("""
                SELECT nombre, dni, telefono, correo
                FROM profesores
                WHERE centro_id = %s
                ORDER BY id
            """, (centro_id,))

            profesores_db = cursor.fetchall()

            st.session_state.profesores = [{
                "nombre": p[0],
                "dni": p[1],
                "telefono": p[2],
                "correo": p[3]
            }
            for p in profesores_db
            ]

            cursor.execute("""
                SELECT id, numero_equipo, nombre_equipo
                FROM equipos
                WHERE centro_id = %s
                ORDER BY numero_equipo
            """, (centro_id,))

            equipos_db = cursor.fetchall()

            equipos_cargados = []

            for equipo in equipos_db:

                equipo_id = equipo[0]

                cursor.execute("""
                    SELECT
                        numero_participante,
                        nombre,
                        apellidos,
                        dni,
                        curso,
                        correo,
                        rol
                    FROM debatientes
                    WHERE equipo_id = %s
                    ORDER BY numero_participante
                """, (equipo_id,))

                debatientes_db = cursor.fetchall()

                miembros = []

                for d in debatientes_db:

                    nombre_completo = f"{d[1]} {d[2]}".strip()

                    miembros.append({
                        "numero_participante": d[0],
                        "nombre": nombre_completo,
                        "dni": d[3],
                        "curso": d[4],
                        "mail": d[5],
                        "rol": d[6]
                    })

                equipos_cargados.append({
                    "numero_equipo": equipo[1],
                    "nombre_equipo": equipo[2],
                    "miembros": miembros
                })
            st.session_state.equipos = equipos_cargados

            st.success("Inscripción encontrada")
            st.session_state.version_carga += 1
            keys_a_conservar = {"modo", "datos_centro", "profesores", "equipos", "version_carga"}
            for key in list(st.session_state.keys()):
                if key not in keys_a_conservar:
                    del st.session_state[key]

            cargar_widgets_desde_session_state()
            st.rerun()
        else:
            st.error("No existe ninguna inscripción con ese correo")

st.markdown(
    "<span style='color:red'>*</span> Campos obligatorios",
    unsafe_allow_html=True
)


    
torneo = st.subheader("II Concurso De Oratoria Para Primaria JMD CHAMBERÍ *")
torneo = "II Concurso De Oratoria Para Primaria JMD CHAMBERÍ"
datos_centro = None


st.subheader("Datos del centro")

datos_centro = st.session_state.datos_centro

denominacion = st.text_input(
    "Denominación del centro *",
    value=datos_centro[1] if datos_centro else ""
)

direccion = st.text_input(
    "Dirección *",
    value=datos_centro[2] if datos_centro else ""
)

localidad = st.text_input(
    "Localidad *",
    value=datos_centro[3] if datos_centro else "",
    key="localidad_centro"
)

provincia = st.text_input(
    "Provincia *",
    value=datos_centro[4] if datos_centro else ""
)

codigo_postal = st.text_input(
    "Código postal *",
    value=datos_centro[5] if datos_centro else ""
)

telefono_centro = st.text_input(
    "Teléfono *",
    value=datos_centro[6] if datos_centro else ""
)

correo_centro = st.text_input(
    "Correo electrónico *",
    value=datos_centro[7] if datos_centro else ""
)

director = st.text_input(
    "Director del centro *",
    value=datos_centro[8] if datos_centro else ""
)

st.subheader("Datos de la convocatoria")
profesores_cargados = st.session_state.profesores
version_carga = st.session_state.version_carga

if modo == "Modificar inscripción" and profesores_cargados:

    num_profesores = len(profesores_cargados)

    num_profesores = st.selectbox(
        "Número de profesores/formadores",
        [1, 2, 3],
        index=num_profesores - 1,
        disabled=True,
        key=f"select_profesores_{version_carga}"
    )

else:

    num_profesores = st.selectbox(
        "Número de profesores/formadores",
        [1, 2, 3],
        index=0,
        key=f"select_profesores_{version_carga}"
    )
    

profesores = []

for i in range(num_profesores):
    datos_profesor = (
        st.session_state.profesores[i]
        if i < len(st.session_state.profesores)
        else {}
    )

    st.markdown(f"### Profesor/Formador {i+1}")

    profesor = st.text_input(
        "Profesor/Formador *",
        value=datos_profesor.get("nombre", ""),
        key=f"profesor_modificar_{version_carga}_{i}"
        )

    dni_profesor = st.text_input(
        "DNI/NIE *",
        value=datos_profesor.get("dni", ""),
        key=f"dni_profesor_modificar_{version_carga}_{i}"
        )

    telefono_profesor = st.text_input(
        "Teléfono del profesor *",
        value=datos_profesor.get("telefono", ""),
        key=f"telefono_profesor_modificar_{version_carga}_{i}"
        )
    

    correo_profesor = st.text_input(
        "Correo electrónico del profesor *",
        value=datos_profesor.get("correo", ""),
        key=f"correo_profesor_modificar_{version_carga}_{i}"
    )

    profesores.append({
        "nombre": profesor,
        "dni": dni_profesor,
        "telefono": telefono_profesor,
        "correo": correo_profesor
    })

st.subheader("Equipos participantes")
equipos_cargados = st.session_state.equipos

if modo == "Modificar inscripción" and equipos_cargados:

    num_equipos = len(equipos_cargados)

    num_equipos = st.selectbox(
        "Número de equipos",
        [1, 2, 3, 4, 5, 6],
        index=num_equipos - 1,
        disabled=True,
        key=f"select_equipos_{version_carga}"
    )

else:

    num_equipos = st.selectbox(
        "Número de equipos",
        [1, 2, 3, 4, 5, 6],
        index=0,
        key=f"select_equipos_{version_carga}"
    )
equipos = []
for i in range(num_equipos):
    datos_equipo = (
        st.session_state.equipos[i]
        if i < len(st.session_state.equipos)
        else {}
    )
    st.markdown("---")
    st.markdown(f"## Equipo {i+1}")
    
    nombre_equipo = st.text_input(
        "Nombre del equipo * ( Tiene que incluir el nombre del centro seguido de una letra identificativa. Ejemplo: CEIP Maximino A)",
        value=datos_equipo.get("nombre_equipo", ""),
        key=f"equipo_modificar_{version_carga}_{i}"
    )
    miembros_cargados = datos_equipo.get("miembros", [])
    if modo == "Modificar inscripción" and miembros_cargados:

        num_miembros = len(miembros_cargados)

        num_miembros = st.selectbox(
            "Número de integrantes",
            [1, 2, 3, 4, 5, 6],
            index=num_miembros - 1,
            disabled=True,
            key=f"num_miembros_{version_carga}_{i}"
        )

    else:

        num_miembros = st.selectbox(
        "Número de integrantes",
        [1, 2, 3, 4, 5, 6],
        index=2,
        key=f"num_miembros_{version_carga}_{i}"
        )

    miembros = []
    for j in range(num_miembros):
        datos_miembro = (
            miembros_cargados[j]
            if j < len(miembros_cargados)
            else {}
        )
        st.markdown(f" Integrante {j+1}")
        nombre = st.text_input(
                "Nombre y apellidos *",
                value=datos_miembro.get("nombre", ""),
                key=f"nombre_modificar_{version_carga}_{i}_{j}"
            )
        dni = st.text_input(
                "DNI/NIE ",
                value=datos_miembro.get("dni", ""),
                key=f"dni_modificar_{version_carga}_{i}_{j}"
            )
        curso = st.text_input(
                "Curso *",
                value=datos_miembro.get("curso", ""),
                key=f"curso_modificar_{version_carga}_{i}_{j}"
            )
        mail = st.text_input(
                "Correo electrónico",
                value=datos_miembro.get("mail", ""),
                key=f"mail_modificar_{version_carga}_{i}_{j}"
            )
        roles = ["Debatiente", "Capitán", "Suplente"]

        rol_actual = datos_miembro.get("rol", "Debatiente")

        indice_rol = (
            roles.index(rol_actual)
            if rol_actual in roles
            else 0
    )

        rol = st.selectbox(
            "Rol *",
            roles,
            index=indice_rol,
            key=f"rol_modificar_{version_carga}_{i}_{j}"
    )
        miembros.append({
            "numero_participante": j + 1,
            "nombre": nombre,
            "dni": dni,
            "curso": curso,
            "mail": mail,
            "rol": rol
            })
    equipos.append({
        "numero_equipo": i + 1,
        "nombre_equipo": nombre_equipo,
        "miembros": miembros
        })
with open("politica_privacidad_goose_talent.pdf", "rb") as pdf_file:
    PDFbyte = pdf_file.read()
    st.markdown(
        "[📄 Consultar política de privacidad](https://github.com/goose-talent/torneo-debate/raw/main/politica_privacidad_goose_talent.pdf)"
        )


privacidad = st.checkbox(
    "Acepto y autorizo a que mis datos sean tratados por GOOSE TALENT, "
    "con la finalidad de remitirme, por cualquier medio, incluidos los electrónicos "
    "(SMS, WhatsApp y correo electrónico), información sobre cualquier curso o "
    "programa actual o futuro de GOOSE TALENT, talleres de orientación y sesiones "
    "informativas, así como recordatorios de las mismas."
    )

if st.button("Enviar solicitud"):
    if not privacidad:
        st.error("Debes aceptar la política de privacidad")
        st.stop()
    if not denominacion.strip():
        st.error("La denominación del centro es obligatoria")
        st.stop()

    if not localidad.strip():
        st.error("La localidad es obligatoria")
        st.stop()

    if not provincia.strip():
        st.error("La provincia es obligatoria")
        st.stop()
        
    if not telefono_centro.strip():
        st.error("El teléfono del centro es obligatorio")
        st.stop()
        
    if not correo_centro.strip():
        st.error("El correo del centro es obligatorio")
        st.stop()
            
    if not director.strip():
        st.error("El director del centro es obligatorio")
        st.stop()
    for profesor_data in profesores:

        if not profesor_data["nombre"].strip():
            st.error("El profesor preparador es obligatorio")
            st.stop()

        if not profesor_data["dni"].strip():
            st.error("El DNI/NIE del profesor es obligatorio")
            st.stop()

        if not validar_dni_nie(profesor_data["dni"]):
            st.error(
                f"El DNI/NIE del profesor {profesor_data['nombre']} no es válido"
            )
            st.stop()

        if not profesor_data["telefono"].strip():
            st.error("El teléfono del profesor es obligatorio")
            st.stop()

        if not profesor_data["correo"].strip():
            st.error("El correo del profesor es obligatorio")
            st.stop()

    sql_torneo = """
    INSERT INTO torneos (nombre)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE
    nombre = VALUES(nombre)
    """
    cursor.execute(sql_torneo, (torneo,))
    conexion.commit()
    cursor.execute("SELECT id FROM torneos WHERE nombre = %s", (torneo,))
    torneo_id = cursor.fetchone()[0]
    for equipo in equipos:
        if not equipo["nombre_equipo"].strip():
            st.error("Todos los equipos deben tener nombre")
            st.stop()
        if len(equipo["miembros"]) == 0:
            st.error(
            f"El equipo {equipo['nombre_equipo']} no tiene participantes")
            st.stop()
        
        sql_centro = """
        INSERT INTO centros (
        torneo_id,
        denominacion,
        direccion,
        localidad,
        provincia,
        codigo_postal,
        telefono,
        correo,
        director
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        direccion = VALUES(direccion),
        localidad = VALUES(localidad),
        provincia = VALUES(provincia),
        codigo_postal = VALUES(codigo_postal),
        telefono = VALUES(telefono),
        correo = VALUES(correo),
        director = VALUES(director)
        """
        cursor.execute(sql_centro, (
            torneo_id,
            denominacion,
            direccion,
            localidad,
            provincia,
            codigo_postal,
            telefono_centro,
            correo_centro,
            director
            ))
        conexion.commit()
        cursor.execute(
            """
            SELECT id
            FROM centros
            WHERE correo = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (correo_centro,)
            )
        centro_id = cursor.fetchone()[0]
        for profesor_data in profesores:
            sql_profesor = """
                INSERT INTO profesores (
                    torneo_id,
                    centro_id,
                    nombre_centro,
                    nombre,
                    dni,
                    telefono,
                    correo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)

                ON DUPLICATE KEY UPDATE
                    nombre = VALUES(nombre),
                    telefono = VALUES(telefono),
                    correo = VALUES(correo),
                    centro_id = VALUES(centro_id),
                    nombre_centro = VALUES(nombre_centro)
                    """
            cursor.execute(sql_profesor, (
                torneo_id,
                centro_id,
                denominacion,
                profesor_data["nombre"],
                profesor_data["dni"],
                profesor_data["telefono"],
                profesor_data["correo"]
                ))
            conexion.commit()
    
        sql_equipo = """
        INSERT INTO equipos (torneo_id,numero_equipo,centro, nombre_equipo,centro_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        nombre_equipo = VALUES(nombre_equipo),
        centro = VALUES(centro),
        centro_id = VALUES(centro_id)
        """
        cursor.execute(sql_equipo, (
            torneo_id,
            equipo["numero_equipo"],
            denominacion,
            equipo["nombre_equipo"],
            centro_id
        ))


        conexion.commit()
        cursor.execute("""
                    SELECT id
                    FROM equipos
                    WHERE torneo_id = %s
                    AND numero_equipo = %s
                    and centro_id = %s
                    """, (torneo_id,equipo["numero_equipo"],centro_id))
        equipo_id = cursor.fetchone()[0]
        for miembro in equipo["miembros"]:
            if not miembro["nombre"].strip():
                st.error("Todos los participantes deben tener nombre")
                st.stop()
            
            if miembro["dni"].strip():
                if not validar_dni_nie(miembro["dni"]):
                    st.error(
                        f"El DNI/NIE de {miembro['nombre']} no es válido"
                        )
                    st.stop()
            if not miembro["curso"].strip():
                st.error(
                    f"El participante {miembro['nombre']} debe tener curso"
                    )
                st.stop()
            if not miembro["rol"].strip():
                st.error(
                    f"El participante {miembro['nombre']} debe tener rol"
                )
                st.stop()
            nombre_completo = miembro["nombre"].split(" ", 1)
            nombre = nombre_completo[0]
            if len(nombre_completo) > 1:
                apellidos = nombre_completo[1]
            else:
                apellidos = ""
            sql_debatiente = """
            INSERT INTO debatientes (
                torneo_id,
                equipo_id,
                numero_participante,
                nombre,
                apellidos,
                dni,
                curso,
                correo,
                rol,
                centro
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre),
            apellidos = VALUES(apellidos),
            dni = VALUES(dni),
            curso = VALUES(curso),
            correo = VALUES(correo),
            rol = VALUES(rol),
            centro = VALUES(centro),
            torneo_id = VALUES(torneo_id),
            equipo_id = VALUES(equipo_id)
            """
            valores = (
                torneo_id,
                equipo_id,
                miembro["numero_participante"],
                nombre,
                apellidos,
                miembro["dni"],
                miembro["curso"],
                miembro["mail"],
                miembro["rol"],
                denominacion
            )
            cursor.execute(sql_debatiente, valores)

    conexion.commit()
    cursor.close()
    conexion.close()

    st.success("Inscripción enviada correctamente")
