DIAGNOSTICOS = {
    "Erro DCD": {
        "causas": [
            "Falha no cilindro DCD",
            "Pressão baixa do gás",
            "Vazamento no sistema criogênico",
            "Sensor DCD com falha",
            "Válvula DCD travada"
        ],
        "pecas": [
            "VALVULA DCD",
            "CRYO CYLINDER",
            "SENSOR DCD",
            "REGULADOR",
            "MANGUEIRA DCD"
        ],
        "checklist": [
            "Verificar pressão do gás",
            "Validar conexão do DCD",
            "Checar vazamentos",
            "Testar sensor DCD",
            "Verificar acionamento da válvula"
        ],
        "prioridade": "ALTA",
        "sla": 8
    },

    "Erro Flow / Fluxo": {
        "causas": [
            "Baixo fluxo de água",
            "Bomba com falha",
            "Filtro obstruído",
            "Sensor de fluxo defeituoso",
            "Mangueira dobrada ou obstruída"
        ],
        "pecas": [
            "BOMBA",
            "FILTRO",
            "FLOW SENSOR",
            "MANGUEIRA",
            "SENSOR NIVEL"
        ],
        "checklist": [
            "Verificar circulação de água",
            "Limpar ou substituir filtro",
            "Testar bomba",
            "Checar mangueiras",
            "Verificar sensor de fluxo"
        ],
        "prioridade": "CRITICA",
        "sla": 4
    },

    "Sem disparo": {
        "causas": [
            "HVPS sem tensão",
            "Capacitor danificado",
            "Shutter travado",
            "Placa principal defeituosa",
            "Interlock aberto"
        ],
        "pecas": [
            "HVPS",
            "CAPACITOR",
            "SHUTTER",
            "MAIN BOARD",
            "INTERLOCK"
        ],
        "checklist": [
            "Medir saída da HVPS",
            "Testar capacitores",
            "Verificar shutter",
            "Checar interlocks",
            "Validar comunicação entre placas"
        ],
        "prioridade": "CRITICA",
        "sla": 4
    },

    "Erro temperatura": {
        "causas": [
            "Superaquecimento",
            "Cooler parado",
            "Sensor de temperatura defeituoso",
            "Falha no chiller",
            "Filtro de ar obstruído"
        ],
        "pecas": [
            "COOLER",
            "TEMP SENSOR",
            "CHILLER",
            "VENTILADOR",
            "FILTRO"
        ],
        "checklist": [
            "Verificar temperatura interna",
            "Checar cooler",
            "Testar sensor",
            "Validar chiller",
            "Limpar filtros"
        ],
        "prioridade": "ALTA",
        "sla": 8
    },

    "Falha de fonte HVPS": {
        "causas": [
            "Fonte de alta tensão com falha",
            "Capacitor em curto ou aberto",
            "Falha de alimentação",
            "Conector solto",
            "Placa de controle da fonte com defeito"
        ],
        "pecas": [
            "HVPS",
            "FONTE ALTA TENSAO",
            "CAPACITOR",
            "CABO HV",
            "PLACA CONTROLE"
        ],
        "checklist": [
            "Verificar tensão de entrada",
            "Medir saída da HVPS",
            "Inspecionar cabos de alta tensão",
            "Verificar capacitores",
            "Checar alarmes no sistema"
        ],
        "prioridade": "CRITICA",
        "sla": 4
    },

    "Falha no aplicador": {
        "causas": [
            "Aplicador com mau contato",
            "Fibra danificada",
            "Lente ou janela suja",
            "Sensor do aplicador com falha",
            "Cabo do handpiece danificado"
        ],
        "pecas": [
            "APLICADOR",
            "FIBRA",
            "LENTE",
            "JANELA",
            "HAND PIECE"
        ],
        "checklist": [
            "Inspecionar aplicador",
            "Verificar fibra",
            "Limpar lente ou janela",
            "Testar cabo",
            "Verificar encaixe do handpiece"
        ],
        "prioridade": "ALTA",
        "sla": 8
    },

    "Falha de sensor": {
        "causas": [
            "Sensor desconectado",
            "Sensor com leitura incorreta",
            "Cabo rompido",
            "Conector oxidado",
            "Falha na placa de leitura"
        ],
        "pecas": [
            "SENSOR",
            "CABO SENSOR",
            "CONECTOR",
            "PLACA SENSOR",
            "SENSOR PRESSAO"
        ],
        "checklist": [
            "Verificar conexão do sensor",
            "Testar continuidade do cabo",
            "Limpar conector",
            "Comparar leitura com referência",
            "Verificar alimentação do sensor"
        ],
        "prioridade": "MEDIA",
        "sla": 24
    },

    "Manutenção preventiva": {
        "causas": [
            "Troca preventiva de filtros",
            "Limpeza programada",
            "Inspeção de mangueiras",
            "Verificação óptica",
            "Revisão geral"
        ],
        "pecas": [
            "FILTRO",
            "MANGUEIRA",
            "LENTE",
            "VEDACAO",
            "KIT PREVENTIVA"
        ],
        "checklist": [
            "Limpar filtros",
            "Inspecionar mangueiras",
            "Verificar vazamentos",
            "Inspecionar lentes",
            "Registrar evidência da preventiva"
        ],
        "prioridade": "BAIXA",
        "sla": 48
    },

    "Outro": {
        "causas": [
            "Falha não classificada",
            "Necessário diagnóstico técnico",
            "Verificar histórico da máquina",
            "Coletar evidências"
        ],
        "pecas": [
            "A DEFINIR"
        ],
        "checklist": [
            "Registrar foto do erro",
            "Descrever sintoma detalhado",
            "Verificar histórico por serial",
            "Consultar supervisor técnico"
        ],
        "prioridade": "MEDIA",
        "sla": 24
    }
}


def analisar_problema(problema):
    if problema in DIAGNOSTICOS:
        return DIAGNOSTICOS[problema]

    return {
        "causas": [
            "Sem diagnóstico disponível"
        ],
        "pecas": [],
        "checklist": [
            "Registrar evidência",
            "Descrever sintoma",
            "Consultar histórico"
        ],
        "prioridade": "MEDIA",
        "sla": 24
    }