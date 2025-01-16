import streamlit as st
import requests
from io import BytesIO
import uuid
import time
import json

# Configuração do cabeçalho com a API Key
HEADERS = {"x-api-key": "1TLezDk8DbaEZ4hZqCBWDrBwPGG5NDo9rL81Zj74"}

# Gerar UUID para a sessão (somente se não estiver já no session_state)
if 'session_uuid' not in st.session_state:
    st.session_state.session_uuid = str(uuid.uuid4())

# URL da API
SIGNED_URL = f"https://izt0vzdtac.execute-api.us-east-1.amazonaws.com/dev/process/{st.session_state.session_uuid}/signed_url"
GET_URL = f"https://izt0vzdtac.execute-api.us-east-1.amazonaws.com/dev/process/{st.session_state.session_uuid}"

# Função para enviar os arquivos e obter as URLs assinadas
def get_signed_urls(index_file, photo_files):
    payload = {
        "index": {
            "filename": index_file.name,
            "metadata": {},
            "content_type": index_file.type,
        },
        "photos": [
            {
                "filename": photo.name,
                "metadata": {},
                "content_type": photo.type,
            }
            for photo in photo_files
        ]
    }

    response = requests.post(SIGNED_URL, json=payload, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        st.toast(f"Erro ao obter URLs assinadas: {response.status_code}", icon="⚠️")
        return None

# Função para fazer upload dos arquivos para as URLs assinadas
def upload_to_s3(signed_urls, index_file, photo_files):
    # Upload do arquivo Index
    if "index" in signed_urls and index_file.name in signed_urls["index"]:
        index_url = signed_urls["index"][index_file.name]["signed_url"]
        index_response = requests.put(index_url, data=index_file.getvalue(), headers={"Content-Type": index_file.type})

        if index_response.status_code == 200:
            st.toast(f"Arquivo Index '{index_file.name}' enviado com sucesso!", icon="✅")
        else:
            st.toast(f"Erro ao enviar arquivo Index: {index_response.status_code}", icon="⚠️")

    # Upload das fotos gerais
    for photo in photo_files:
        photo_name = photo.name
        signed_url_data = next((item[photo_name] for item in signed_urls['photos'] if photo_name in item), None)

        if signed_url_data:
            signed_url = signed_url_data['signed_url']
            photo_response = requests.put(signed_url, data=photo.getvalue(), headers={"Content-Type": photo.type})

            if photo_response.status_code == 200:
                st.toast(f"Foto '{photo_name}' enviada com sucesso!", icon="✅")
            else:
                st.toast(f"Erro ao enviar foto '{photo_name}': {photo_response.status_code}", icon="⚠️")

# Função para buscar dados periodicamente
def fetch_data():
    response = requests.get(GET_URL, headers=HEADERS)

    if response.status_code == 200:
        st.toast(f"Resultados Encontrados", icon="✅")
        return response.json()
    else:
        st.toast(f"Buscando Resultados", icon="🔍")
        return None

# Função para ler o arquivo JSON da URL
def read_json_from_s3(result_url):
    response = requests.get(result_url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.toast(f"Erro ao acessar o arquivo JSON no S3: {response.status_code}", icon="⚠️")
        return None

# Função para exibir fotos e informações inline
def display_photos_with_info(valid_photos, invalid_photos, all_photos):
    # Função para formatar o status com cores
    def status_colored(status):
        if status == "Válida":
            return f'<span style="color:green; font-weight:bold;">{status}</span>'
        elif status == "Inválida":
            return f'<span style="color:red; font-weight:bold;">{status}</span>'
        return status

    # Processando fotos válidas
    st.header("Fotos Válidas")
    for photo in valid_photos:
        photo_url = next((all_photo['url'] for all_photo in all_photos if all_photo['photo_id'] == photo['photo_id']), None)
        if photo_url:
            cols = st.columns([3, 3, 6])
            with cols[0]:
                st.markdown(f"<div style='display: flex; justify-content: center; align-items: center; height: 100%;'>{status_colored('Válida')}</div>", unsafe_allow_html=True)
            with cols[1]:
                st.write("")  # Espaço vazio
            with cols[2]:
                st.image(photo_url, caption=f"Foto ID: {photo['photo_id']}", use_column_width=True)

    # Processando fotos inválidas
    st.header("Fotos Inválidas")
    for invalid_type, photos in invalid_photos.items():
        for photo in photos:
            photo_url = next((all_photo['url'] for all_photo in all_photos if all_photo['photo_id'] == photo['photo_id']), None)
            if photo_url:
                cols = st.columns([3, 3, 6])
                with cols[0]:
                    st.markdown(f"<div style='display: flex; justify-content: center; align-items: center; height: 100%;'>{status_colored('Inválida')}</div>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div style='display: flex; justify-content: center; align-items: center; height: 100%;'>{invalid_type.replace('_', ' ').title()}</div>", unsafe_allow_html=True)
                with cols[2]:
                    st.image(photo_url, caption=f"Foto ID: {photo['photo_id']}", use_column_width=True)

# Função para exibir o JSON de forma compacta
def display_json(json_data):
    st.markdown("**Resultado em JSON**")
    st.json(json_data)

# Título da aplicação
st.title("Processamento de Fotos e Upload")

# Seção 1: Upload de arquivos
st.header("Upload de Arquivos")
index_file = st.file_uploader("Selecione a foto de identificação", type=["jpg", "jpeg", "png"], key="index")
photo_files = st.file_uploader("Selecione as fotos para análise", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if st.button("Iniciar Processamento"):
    if index_file and photo_files:
        # Obter URLs assinadas
        response_data = get_signed_urls(index_file, photo_files)
        
        if response_data:
            upload_to_s3(response_data, index_file, photo_files)

            with st.expander("Monitoramento em Tempo Real"):
                placeholder = st.empty()
                processing = True

                while processing:
                    data = fetch_data()

                    if data:
                        with placeholder.container():
                            st.write(f"**Process ID:** {data['process_id']}")
                            st.write(f"**Status:** {data['status']}")
                            st.write(f"**Fotos processadas:** {data['processed_count']} de {data['total_count']}")

                            if 'result_url' in data:
                                json_data = read_json_from_s3(data['result_url'])

                                if json_data:
                                    st.header("Fotos Processadas")
                                    invalid_photos = json_data.get('invalid_photos', {})
                                    valid_photos = json_data.get('valid_photos', [])
                                    display_photos_with_info(valid_photos, invalid_photos, data['photos'])

                                    # Exibir o JSON
                                    display_json(json_data)

                                processing = False
                    time.sleep(3)
    else:   
        st.toast("Por favor, selecione o arquivo Index e pelo menos uma foto", icon="⚠️")

# Exibir o UUID da sessão no rodapé
st.markdown(f"<p style='font-size:10px; text-align:right;'>Session UUID: {st.session_state.session_uuid}</p>", unsafe_allow_html=True)
