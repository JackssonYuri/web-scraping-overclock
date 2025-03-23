from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd
import time

#Inicialização do Navegador 
def iniciar_Driver():
    service = Service()
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    options.add_argument("--start-maximized")

    return driver

def pegar_produtos(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "t4s-product-title")))
    produtos = driver.find_elements(By.CLASS_NAME, "t4s-product-title")
    
    # Coleta o nome e o link do produto
    lista_produtos = []
    for produto in produtos:
        try:
            nome = produto.text.strip()
            link = produto.find_element(By.TAG_NAME, "a").get_attribute("href")  # Obtém a URL do produto
            lista_produtos.append((nome, link))
        except:
            continue

    return lista_produtos

def pegar_precos(driver):
    precos_lista = driver.find_elements(By.CLASS_NAME, "t4s-product-price")
    precos_corrigidos = []
    
    for preco_elemento in precos_lista:
        preco_atual = preco_elemento.find_elements(By.TAG_NAME, "ins")
        preco_original = preco_elemento.find_elements(By.TAG_NAME, "del")

        if preco_atual:  # Produto em promoção
            preco_corrigido = preco_atual[0].text.strip()
            preco_normal = preco_original[0].text.strip() if preco_original else "N/A"
            precos_corrigidos.append(f"{preco_normal} → {preco_corrigido}")
        else:  # Produto sem promoção
            precos_corrigidos.append(preco_elemento.text.strip())

    return precos_corrigidos

def pegar_avaliacoes(driver):
    avaliacoes = driver.find_elements(By.CLASS_NAME, "jdgm-prev-badge__text")
    return [avaliacao.text.strip() for avaliacao in avaliacoes]

def pegar_sabores(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "t4s-swatch__item"))
        )

        sabores_elements = driver.find_elements(By.CLASS_NAME, "t4s-swatch__item")
        if not sabores_elements:
            return "N/A"
        
        sabores = [sabor.get_attribute("data-value") for sabor in sabores_elements]

        return sabores
    except:
        return "N/A"

def pegar_descricao_produto(driver, url):
    """Abre a página do produto, coleta a descrição e volta para a lista."""
    
    driver.get(url)
    time.sleep(5)  # Tempo para carregar a página do produto e conseguir pegar tudo tranquilamente
    
    try:
        descricao_elemento = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='t4s-liquid_'][class*='t4s-pr__custom-liquid']"))
        )
        
        # Tenta pegar os parágrafos dentro da descrição
        paragrafos = descricao_elemento.find_elements(By.TAG_NAME, "p")
        textos = [p.text.strip() for p in paragrafos if p.text.strip()]
        
        # Se não houver parágrafos válidos, retorna "N/A"
        if not textos:
            return "N/A"

        # Se algum texto contiver "Parcele", retorna "N/A", esse é caso de alguns produtos que tem somente essa parte de parcelamento como texto
        if any("Parcele" in texto for texto in textos):
            descricao = driver.find_elements(By.CLASS_NAME, "t4s-rte")[1]

            descricao = descricao.text

            return descricao

        # Retorna o último parágrafo válido
        return textos[-1]

    except Exception as e:
        print(f"Erro ao obter descrição: {e}")
        return "N/A"
    

def pegar_imagem_produto(driver):
    """Captura a URL da imagem principal do produto"""
    try:
        imagem_elemento = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.t4s-lz--fadeIn"))
        )
        # Tenta pegar primeiro do data-master
        imagem_url = imagem_elemento.get_attribute("data-master")
        if not imagem_url:
            # Se não encontrar, tenta pegar do data-srcset (pega a primeira URL)
            imagem_url = imagem_elemento.get_attribute("data-srcset").split(",")[0].split(" ")[0]
        
        # A URL no data-master pode estar sem o https:// no início, então garantimos que fique correta
        if imagem_url.startswith("//"):
            imagem_url = "https:" + imagem_url
        
        return imagem_url
    except Exception as e:
        print("Erro ao pegar imagem:", e)
        return "N/A"

def pegar_tabela_nutricional(driver):
    """Captura a URL da imagem da tabela nutricional na maior resolução (1600w)"""
    try:
        # Espera até que pelo menos 5 imagens sejam carregadas
        imagens = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "img.t4s-lz--fadeIn"))
        )

        # Verifica se há pelo menos 5 elementos
        if len(imagens) < 5:
            raise ValueError("Menos de 5 imagens encontradas.")

        # Seleciona a 5ª imagem (índice 4, pois começa em 0)
        imagem = imagens[4]
        srcset = imagem.get_attribute("srcset")

        if not srcset:
            raise ValueError("Atributo 'srcset' não encontrado na imagem.")

        # Separa as URLs pelo formato do srcset
        urls = srcset.split(", ")

        # Filtra a URL com resolução 1600w (melhor qualidade)
        url_1600 = next((url.split(" ")[0] for url in urls if "1600w" in url), None)

        if not url_1600:
            raise ValueError("URL com 1600w não encontrada.")

        # Adiciona "https:" se necessário
        if url_1600.startswith("//"):
            url_1600 = "https:" + url_1600

        return url_1600

    except Exception as e:
        print("Erro ao pegar imagem da tabela nutricional:", e)
        return "N/A"
    
def coletar_dados(driver, url):
    driver.get(url)
    
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "t4s-product-title")))

    produtos_links = pegar_produtos(driver)
    precos = pegar_precos(driver)
    avaliacoes = pegar_avaliacoes(driver)
    sabores = pegar_sabores(driver)
    tabela_nutricional = pegar_tabela_nutricional(driver)

    
    sabores_lista = []
    descricoes = []
    imagens = []
    tabelas_nutricionais = []

    for nome, link in produtos_links:
        descricao = pegar_descricao_produto(driver, link)  # Acessa a página do produto e pega a descrição
        sabores = pegar_sabores(driver)  
        imagem = pegar_imagem_produto(driver)
        tabela_nutricional = pegar_tabela_nutricional(driver)

        descricoes.append(descricao)
        sabores_lista.append(sabores if isinstance(sabores, list) else [sabores])
        imagens.append(imagem)
        tabelas_nutricionais.append(tabela_nutricional)

    # Ajusta os tamanhos das listas para evitar erro no DataFrame
    max_len = max(len(produtos_links), len(precos), len(avaliacoes), len(sabores), len(descricoes), len(imagens), len(tabelas_nutricionais))
    produtos_links += [("N/A", "N/A")] * (max_len - len(produtos_links))
    precos += ["N/A"] * (max_len - len(precos))
    avaliacoes += ["N/A"] * (max_len - len(avaliacoes))
    sabores += ["N/A"] * (max_len - len(sabores))
    descricoes += ["N/A"] * (max_len - len(descricoes))
    imagens += ["N/A"] * (max_len - len(imagens))
    tabelas_nutricionais += ["N/A"] * (max_len - len(tabelas_nutricionais))

    return pd.DataFrame({
        "Produto": [p[0] for p in produtos_links],  # Apenas os nomes dos produtos
        "Preço": precos,
        "Sabores": [" | ".join(s) for s in sabores_lista],  # Formata a lista de sabores
        "Avaliação": avaliacoes,
        "Descrição": descricoes,
        "Imagem": imagens,
        "Tabela Nutricional": tabelas_nutricionais
    })

if __name__ == "__main__":
    driver = iniciar_Driver()

    # Passando as duas páginas de produtos
    urls = [
        "https://bebaoverclock.com.br/collections/colecao?page=1",
        "https://bebaoverclock.com.br/collections/colecao?page=2"
    ]

    df_final = pd.concat([coletar_dados(driver, url) for url in urls], ignore_index=True)

    print(df_final)

    df_final.to_csv("produtos_overclock.csv", index=False, encoding="utf-8-sig")


    driver.quit()
