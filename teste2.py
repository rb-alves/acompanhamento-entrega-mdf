import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

BASE_URL = "https://api.umov.me/CenterWeb/api"
TOKEN = "35891ee0f175019de59e6e440f092578b0317a"

# atividades que queremos
DESIRED_ACTIVITIES = {"Entrega", "Entrega não realizada"}

def get_xml(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return ET.fromstring(resp.text)

def get_schedule_ids(transacao):
    url = f"{BASE_URL}/{TOKEN}/schedule.xml?transacao={transacao}"
    root = get_xml(url)
    return [e.attrib["id"] for e in root.findall(".//entry")]

def get_schedule_details(schedule_id):
    url = f"{BASE_URL}/{TOKEN}/schedule/{schedule_id}.xml"
    root = get_xml(url)

    # verifica se situação é cancelada
    situation = root.find(".//situation/description")
    if situation is not None and situation.text == "Cancelada":
        return None

    # tipo da tarefa (ex: Entrega)
    tipo_tarefa = root.findtext(".//scheduleType/description")

    # dados iniciais
    insert_dt = root.findtext(".//insertDateTime")
    n_pedido = root.findtext(".//customFields/n__pedido")
    loja = root.findtext(".//customFields/loja")
    motorista = root.findtext(".//agent/name")

    # lista de IDs de atividades
    activities = [a.attrib["id"] for a in root.findall(".//activities/activity")]

    return {
        "schedule_id": schedule_id,
        "insertDateTime": insert_dt,
        "n_pedido": n_pedido,
        "loja": loja,
        "motorista": motorista,
        "tipo_tarefa": tipo_tarefa,
        "activities": activities
    }

def get_activity_history(schedule_id, start="2025-01-01 08:00:00", end="2035-12-31 23:59:59"):
    url = f"{BASE_URL}/{TOKEN}/activityHistory.xml?initialStartTimeOnSystem={quote_plus(start)}&endStartTimeOnSystem={quote_plus(end)}&schedule={schedule_id}"
    root = get_xml(url)
    return [e.attrib["id"] for e in root.findall(".//entry")]

def get_activity_history_details(history_id):
    url = f"{BASE_URL}/{TOKEN}/activityHistory/{history_id}.xml"
    root = get_xml(url)
    activity = root.find(".//activity")
    if activity is None:
        return None

    description = activity.findtext("description")
    if description not in DESIRED_ACTIVITIES:
        return None

    finish_time = root.findtext(".//finishTimeOnSystem") or root.findtext(".//endTimeSync")
    status = root.findtext(".//status")

    return {
        "activity_id": activity.findtext("id"),
        "activity_description": description,
        "finish_time": finish_time,
        "status": status
    }

# ----------- fluxo principal -----------
def fetch_entrega(transacao):
    schedules = get_schedule_ids(transacao)
    resultados = []

    for sched_id in schedules:
        details = get_schedule_details(sched_id)
        if not details:
            continue

        histories = get_activity_history(sched_id)
        entregas = []

        for h_id in histories:
            hist = get_activity_history_details(h_id)
            if hist:
                entregas.append(hist)

        if entregas:
            for e in entregas:
                resultados.append({
                    "tipo_tarefa": details["tipo_tarefa"],
                    "activity_id": e["activity_id"],
                    "activity_description": e["activity_description"],
                    "insert_time": details["insertDateTime"],
                    "finish_time": e["finish_time"],
                    "status": e["status"],
                    "n_pedido": details["n_pedido"],
                    "loja": details["loja"],
                    "motorista": details["motorista"]
                })
        else:
            resultados.append({
                "tipo_tarefa": details["tipo_tarefa"],
                "insert_time": details["insertDateTime"],
                "n_pedido": details["n_pedido"],
                "loja": details["loja"],
                "motorista": details["motorista"]
            })
    return resultados

# ----------------- exemplo -----------------
if __name__ == "__main__":
    transacao = "351788"
    res = fetch_entrega(transacao)
    for r in res:
        print("Tipo de tarefa:", r["tipo_tarefa"])
        if "activity_id" in r:
            print("----")
            print(f"Activity ID: {r['activity_id']} ({r['activity_description']})")
            print(f"Data/Hora inserção da tarefa: {r['insert_time']}")
            print(f"Hora finalização da atividade: {r['finish_time']}")
            print(f"Status execução: {r['status']}")
            print(f"Nº Pedido: {r['n_pedido']}")
            print(f"Loja: {r['loja']}")
            print(f"Motorista: {r['motorista']}")
            print("----")
        else:
            print(f"Data/Hora inserção da tarefa: {r['insert_time']}")
            print(f"Nº Pedido: {r['n_pedido']}")
            print(f"Loja: {r['loja']}")
            print(f"Motorista: {r['motorista']}")
        print()
